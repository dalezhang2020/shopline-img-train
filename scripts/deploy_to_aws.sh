#!/bin/bash
# ============================================================================
# AWS 部署脚本 - 快速部署 SKU 识别 API 到 AWS 服务器
# ============================================================================
#
# 功能：
#   1. 上传向量数据库文件到 AWS 服务器
#   2. 拉取最新 Docker 镜像
#   3. 重启 API 服务
#   4. 验证部署成功
#
# 使用方法：
#   ./scripts/deploy_to_aws.sh [选项]
#
# 选项：
#   --skip-embeddings    跳过上传向量数据库（如果文件未变化）
#   --skip-docker        跳过 Docker 镜像更新（仅重启服务）
#   --dry-run            模拟运行，不执行实际操作
#
# ============================================================================

set -e  # 遇到错误立即退出

# ============================================================================
# 配置变量（请根据实际情况修改）
# ============================================================================

# AWS 服务器配置
AWS_SERVER_USER="${AWS_SERVER_USER:-your-user}"
AWS_SERVER_HOST="${AWS_SERVER_HOST:-your-aws-server}"
AWS_SERVER_PATH="${AWS_SERVER_PATH:-/opt/sku_recognition}"

# GitLab Container Registry
GITLAB_REGISTRY="${CI_REGISTRY:-registry.gitlab.com}"
GITLAB_IMAGE="${CI_REGISTRY_IMAGE:-registry.gitlab.com/your-group/shopline-img-train}"

# 本地路径
LOCAL_EMBEDDINGS_DIR="data/embeddings"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# 辅助函数
# ============================================================================

print_step() {
    echo -e "${BLUE}==>${NC} ${1}"
}

print_success() {
    echo -e "${GREEN}✓${NC} ${1}"
}

print_error() {
    echo -e "${RED}✗${NC} ${1}"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} ${1}"
}

check_prerequisites() {
    print_step "检查前置条件..."

    # 检查 rsync
    if ! command -v rsync &> /dev/null; then
        print_error "rsync 未安装，请安装: brew install rsync (macOS) 或 apt install rsync (Ubuntu)"
        exit 1
    fi

    # 检查 SSH 连接
    if ! ssh -o ConnectTimeout=5 "$AWS_SERVER_USER@$AWS_SERVER_HOST" "exit" 2>/dev/null; then
        print_error "无法连接到 AWS 服务器: $AWS_SERVER_USER@$AWS_SERVER_HOST"
        print_warning "请检查 SSH 配置和服务器地址"
        exit 1
    fi

    # 检查本地向量数据库文件
    if [ ! -f "$LOCAL_EMBEDDINGS_DIR/faiss_index_robust_5x.bin" ]; then
        print_error "向量数据库文件不存在: $LOCAL_EMBEDDINGS_DIR/faiss_index_robust_5x.bin"
        exit 1
    fi

    print_success "前置条件检查通过"
}

upload_embeddings() {
    print_step "上传向量数据库到 AWS 服务器..."

    # 显示文件大小
    FAISS_SIZE=$(du -h "$LOCAL_EMBEDDINGS_DIR/faiss_index_robust_5x.bin" | cut -f1)
    META_SIZE=$(du -h "$LOCAL_EMBEDDINGS_DIR/sku_metadata_robust_5x.pkl" | cut -f1)
    print_warning "文件大小: FAISS=$FAISS_SIZE, Metadata=$META_SIZE"

    if [ "$DRY_RUN" = true ]; then
        print_warning "[DRY RUN] 跳过实际上传"
        return
    fi

    # 使用 rsync 上传（支持断点续传和增量更新）
    rsync -avz --progress \
        "$LOCAL_EMBEDDINGS_DIR/" \
        "$AWS_SERVER_USER@$AWS_SERVER_HOST:$AWS_SERVER_PATH/data/embeddings/"

    print_success "向量数据库上传完成"
}

pull_docker_image() {
    print_step "拉取最新 Docker 镜像..."

    if [ "$DRY_RUN" = true ]; then
        print_warning "[DRY RUN] 跳过 Docker 镜像拉取"
        return
    fi

    ssh "$AWS_SERVER_USER@$AWS_SERVER_HOST" << EOF
        cd $AWS_SERVER_PATH
        docker-compose -f docker-compose.api.yml pull
EOF

    print_success "Docker 镜像拉取完成"
}

restart_api_service() {
    print_step "重启 API 服务..."

    if [ "$DRY_RUN" = true ]; then
        print_warning "[DRY RUN] 跳过服务重启"
        return
    fi

    ssh "$AWS_SERVER_USER@$AWS_SERVER_HOST" << EOF
        cd $AWS_SERVER_PATH
        docker-compose -f docker-compose.api.yml up -d
        echo "等待服务启动..."
        sleep 10
EOF

    print_success "API 服务重启完成"
}

verify_deployment() {
    print_step "验证部署..."

    if [ "$DRY_RUN" = true ]; then
        print_warning "[DRY RUN] 跳过验证"
        return
    fi

    # 检查容器状态
    print_warning "检查容器状态..."
    ssh "$AWS_SERVER_USER@$AWS_SERVER_HOST" << EOF
        cd $AWS_SERVER_PATH
        docker-compose -f docker-compose.api.yml ps
EOF

    # 测试健康检查 API
    print_warning "测试健康检查 API..."
    HEALTH_URL="https://tools.zgallerie.com/sku_recognition_fastapi/api/v1/health"

    sleep 5  # 等待服务完全启动

    if curl -f -s "$HEALTH_URL" > /dev/null; then
        print_success "✅ API 健康检查通过！"
        echo ""
        curl -s "$HEALTH_URL" | python3 -m json.tool 2>/dev/null || curl -s "$HEALTH_URL"
    else
        print_error "API 健康检查失败！"
        print_warning "查看日志:"
        ssh "$AWS_SERVER_USER@$AWS_SERVER_HOST" << EOF
            cd $AWS_SERVER_PATH
            docker-compose -f docker-compose.api.yml logs --tail=50
EOF
        exit 1
    fi
}

show_logs() {
    print_step "显示最近日志..."

    ssh "$AWS_SERVER_USER@$AWS_SERVER_HOST" << EOF
        cd $AWS_SERVER_PATH
        docker-compose -f docker-compose.api.yml logs --tail=30
EOF
}

# ============================================================================
# 主函数
# ============================================================================

main() {
    echo "============================================================"
    echo "  SKU 识别 API - AWS 部署脚本"
    echo "============================================================"
    echo ""

    # 解析命令行参数
    SKIP_EMBEDDINGS=false
    SKIP_DOCKER=false
    DRY_RUN=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-embeddings)
                SKIP_EMBEDDINGS=true
                shift
                ;;
            --skip-docker)
                SKIP_DOCKER=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            -h|--help)
                echo "使用方法: $0 [选项]"
                echo ""
                echo "选项:"
                echo "  --skip-embeddings    跳过上传向量数据库"
                echo "  --skip-docker        跳过 Docker 镜像更新"
                echo "  --dry-run            模拟运行"
                echo "  -h, --help           显示帮助信息"
                echo ""
                echo "环境变量:"
                echo "  AWS_SERVER_USER      AWS 服务器用户名 (默认: your-user)"
                echo "  AWS_SERVER_HOST      AWS 服务器地址 (默认: your-aws-server)"
                echo "  AWS_SERVER_PATH      部署路径 (默认: /opt/sku_recognition)"
                exit 0
                ;;
            *)
                print_error "未知参数: $1"
                exit 1
                ;;
        esac
    done

    # 显示配置
    echo "配置:"
    echo "  服务器: $AWS_SERVER_USER@$AWS_SERVER_HOST"
    echo "  路径: $AWS_SERVER_PATH"
    echo "  跳过向量数据库: $SKIP_EMBEDDINGS"
    echo "  跳过 Docker 更新: $SKIP_DOCKER"
    echo "  模拟运行: $DRY_RUN"
    echo ""

    # 执行部署步骤
    check_prerequisites

    if [ "$SKIP_EMBEDDINGS" = false ]; then
        upload_embeddings
    else
        print_warning "跳过向量数据库上传"
    fi

    if [ "$SKIP_DOCKER" = false ]; then
        pull_docker_image
    else
        print_warning "跳过 Docker 镜像更新"
    fi

    restart_api_service
    verify_deployment

    echo ""
    echo "============================================================"
    print_success "🚀 部署完成！"
    echo "============================================================"
    echo ""
    echo "API 端点:"
    echo "  健康检查: https://tools.zgallerie.com/sku_recognition_fastapi/api/v1/health"
    echo "  API 文档: https://tools.zgallerie.com/sku_recognition_fastapi/docs"
    echo ""
    echo "常用命令:"
    echo "  查看日志: ssh $AWS_SERVER_USER@$AWS_SERVER_HOST 'cd $AWS_SERVER_PATH && docker-compose -f docker-compose.api.yml logs -f'"
    echo "  重启服务: ssh $AWS_SERVER_USER@$AWS_SERVER_HOST 'cd $AWS_SERVER_PATH && docker-compose -f docker-compose.api.yml restart'"
    echo "  停止服务: ssh $AWS_SERVER_USER@$AWS_SERVER_HOST 'cd $AWS_SERVER_PATH && docker-compose -f docker-compose.api.yml down'"
    echo ""
}

# 运行主函数
main "$@"
