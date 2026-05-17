# GitHub Wiki 同步指南

由于当前网络环境无法直接连接 GitHub，请稍后在能够访问 GitHub 的环境下执行以下步骤。

## 方法一：使用自动脚本（推荐）

```bash
cd D:/soso/projects/hermes-desktop
bash sync-wiki-to-github.sh
```

## 方法二：手动同步

### 步骤 1：克隆 GitHub Wiki 仓库

```bash
git clone https://github.com/octave-12/hermes-desktop.wiki.git
cd hermes-desktop.wiki
```

### 步骤 2：克隆 Gitee Wiki 仓库（作为源）

```bash
git clone https://gitee.com/octave-12/hermes-desktop.wiki.git ../gitee-wiki
```

### 步骤 3：复制文件

```bash
# 复制所有文件（除了 .git 目录）
cp -r ../gitee-wiki/* .
rm -rf .gitignore  # 如果有的话
```

### 步骤 4：提交并推送

```bash
git add .
git commit -m "同步 Gitee Wiki 最新内容"
git push origin master
```

## 方法三：从本地文件同步

如果本地有 `docs/wiki/` 目录：

```bash
# 1. 克隆 GitHub Wiki
git clone https://github.com/octave-12/hermes-desktop.wiki.git
cd hermes-desktop.wiki

# 2. 复制本地 Wiki 文件
cp -r ../docs/wiki/content/* .

# 3. 提交推送
git add .
git commit -m "更新 Wiki 文档"
git push origin master
```

## 注意事项

1. GitHub Wiki 仓库地址格式：`https://github.com/用户名/仓库名.wiki.git`
2. Gitee Wiki 仓库地址格式：`https://gitee.com/用户名/仓库名.wiki.git`
3. Wiki 仓库默认分支是 `master`（不是 `main`）
4. 首页文件名应为 `Home.md`

## 当前同步状态

- ✅ Gitee 主仓库：https://gitee.com/octave-12/hermes-desktop
- ✅ Gitee Wiki：https://gitee.com/octave-12/hermes-desktop/wikis
- ✅ GitHub 主仓库：https://github.com/octave-12/hermes-desktop
- ⏳ GitHub Wiki：待同步（https://github.com/octave-12/hermes-desktop/wiki）

## 网络问题排查

如果遇到连接超时：

```bash
# 测试连接
ping github.com
curl -I https://github.com

# 尝试使用 SSH
git clone git@github.com:octave-12/hermes-desktop.wiki.git

# 或设置代理（如果有）
git config --global http.proxy http://127.0.0.1:端口号
```
