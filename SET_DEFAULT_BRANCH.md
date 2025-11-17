# 设置默认分支为 claude/sku-recognition-system-0143ogM7hB81TdFB2vABqoGR

## 🎯 目标

将 `claude/sku-recognition-system-0143ogM7hB81TdFB2vABqoGR` 设置为仓库的默认分支，使其成为：
- 克隆仓库时默认检出的分支
- GitHub 仓库页面默认显示的分支
- PR 的默认目标分支

## 📝 在 GitHub 网页端设置（推荐）

### 步骤 1: 访问仓库设置

1. 打开浏览器，访问仓库地址：
   ```
   https://github.com/dalezhang2020/shopline-img-train
   ```

2. 点击仓库页面右上角的 **Settings** (设置) 按钮
   - 如果看不到 Settings，说明您需要管理员权限

### 步骤 2: 更改默认分支

1. 在左侧菜单中，确保您在 **General** (常规) 设置页面

2. 找到 **Default branch** (默认分支) 部分

3. 点击分支名称右侧的 **切换按钮** (双箭头图标) ⇄

4. 在弹出的对话框中：
   - 搜索或选择分支：`claude/sku-recognition-system-0143ogM7hB81TdFB2vABqoGR`
   - 点击 **Update** 按钮

5. 在确认对话框中：
   - 阅读警告信息（关于 PR 和状态检查的影响）
   - 点击 **I understand, update the default branch** 确认

### 步骤 3: 验证设置

1. 返回仓库主页：`https://github.com/dalezhang2020/shopline-img-train`

2. 检查页面左上角的分支选择器，应该显示：
   ```
   claude/sku-recognition-system-0143ogM7hB81TdFB2vABqoGR
   ```

3. 测试克隆（可选）：
   ```bash
   # 在新目录中测试克隆，验证默认分支
   git clone https://github.com/dalezhang2020/shopline-img-train.git test-clone
   cd test-clone
   git branch --show-current
   # 应该输出: claude/sku-recognition-system-0143ogM7hB81TdFB2vABqoGR
   ```

## 🔧 使用 GitHub CLI (备选方法)

如果您在本地有 GitHub CLI (`gh`) 并且已经认证，可以使用以下命令：

```bash
# 方法 1: 使用 gh repo edit
gh repo edit dalezhang2020/shopline-img-train \
  --default-branch claude/sku-recognition-system-0143ogM7hB81TdFB2vABqoGR

# 方法 2: 使用 gh api
gh api repos/dalezhang2020/shopline-img-train -X PATCH \
  -f default_branch='claude/sku-recognition-system-0143ogM7hB81TdFB2vABqoGR'
```

## ⚠️ 注意事项

### 设置默认分支的影响

1. **Pull Requests**
   - 新创建的 PR 将默认合并到此分支
   - 现有 PR 不会受影响

2. **克隆和检出**
   - `git clone` 将默认检出此分支
   - 现有的本地克隆不会受影响

3. **分支保护**
   - 如果原默认分支有分支保护规则，建议为新默认分支设置相同规则
   - 在 Settings → Branches → Branch protection rules 中设置

4. **CI/CD**
   - 检查 GitHub Actions 等 CI/CD 工作流是否依赖于默认分支
   - 可能需要更新工作流配置

### 其他分支的清理

设置新默认分支后，建议删除不再使用的旧分支：

1. 在 GitHub 仓库页面，点击 **Branches** 标签
2. 找到要删除的分支：
   - `claude/image-augmentation-enhancement-01YEyReYjuetxYCDHXUJXeh8`
   - `claude/scrape-shopline-data-01YJpnD6RKj61S2R2yPMyC6K`
3. 点击每个分支右侧的 **垃圾桶图标** 🗑️ 删除

**注意**: 删除前确认这些分支的功能已整合到主分支中。

## ✅ 完成检查清单

- [ ] 在 GitHub Settings 中将默认分支设置为 `claude/sku-recognition-system-0143ogM7hB81TdFB2vABqoGR`
- [ ] 验证仓库主页显示正确的默认分支
- [ ] （可选）测试 `git clone` 克隆正确的分支
- [ ] （可选）为新默认分支设置分支保护规则
- [ ] （可选）删除已过时的其他分支
- [ ] （可选）更新 CI/CD 工作流配置（如有需要）

## 📚 相关文档

- [BRANCH_INFO.md](BRANCH_INFO.md) - 分支说明
- [README_BRANCHES.txt](README_BRANCHES.txt) - 快速参考
- [GitHub 官方文档：更改默认分支](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-branches-in-your-repository/changing-the-default-branch)

## 🔗 快速链接

- **仓库地址**: https://github.com/dalezhang2020/shopline-img-train
- **设置页面**: https://github.com/dalezhang2020/shopline-img-train/settings
- **分支列表**: https://github.com/dalezhang2020/shopline-img-train/branches

---

**设置完成后，克隆仓库将更加简洁**：

```bash
# 之前需要指定分支
git clone -b claude/sku-recognition-system-0143ogM7hB81TdFB2vABqoGR \
  https://github.com/dalezhang2020/shopline-img-train.git

# 设置默认分支后，可以直接克隆
git clone https://github.com/dalezhang2020/shopline-img-train.git
```
