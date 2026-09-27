# Research2Slides 0.2.0 Windows 本地完整包

包内包含 Python wheel 及全部运行依赖 wheels、PptxGenJS Renderer 源码与编译产物、`node_modules`、离线测试样例和校验和。

前置条件：Windows、Python 3.11+、Node.js 20+。安装过程不访问网络。

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
powershell -ExecutionPolicy Bypass -File .\verify.ps1
```

日常调用：

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1 version
powershell -ExecutionPolicy Bypass -File .\run.ps1 doctor --require-renderer
```

`verify.ps1` 会在包内生成 `smoke_workspace`，完整运行离线 parse、understand、plan、spec、render、Semantic QA 和 package，但跳过 PowerPoint/LibreOffice PDF 导出。
