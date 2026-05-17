# 启用 GitHub Wiki 并同步指南

## 问题原因
GitHub 的 Wiki 功能默认可能是关闭的，需要先启用。

## 启用步骤

### 1. 访问 GitHub 仓库设置
打开：https://github.com/octave-12/hermes-desktop/settings

### 2. 启用 Wiki
在设置页面中：
- 找到 "Features" 部分
- 勾选 "Wikis"
- 保存设置

### 3. 同步 Wiki
启用后，执行以下脚本：

```bash
#!/bin/bash
cd D:/soso/projects/hermes-desktop

# 克隆两个 Wiki
git clone https://github.com/octave-12/hermes-desktop.wiki.git github-wiki-temp
git clone https://gitee.com/octave-12/hermes-desktop.wiki.git gitee-wiki-temp

# 复制内容
cp -r gitee-wiki-temp/* github-wiki-temp/

# 提交推送
cd github-wiki-temp
git config user.email "octave-12@gitee.com"
git config user.name "octave-12"
git add .
git commit -m "同步 Gitee Wiki"
git push origin master

# 清理
cd ..
rm -rf github-wiki-temp gitee-wiki-temp
```

## 快速验证

启用 Wiki 后，访问：
https://github.com/octave-12/hermes-desktop/wiki

---

创建时间：2026-05-17
