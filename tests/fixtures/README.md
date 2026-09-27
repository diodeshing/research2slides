# Integration fixtures

这些 fixture 用原创的最小文本和图形模拟两篇公开 AI 论文的结构，不包含论文全文或原始论文图像：

- **Attention Is All You Need**, Vaswani et al., 2017 — https://arxiv.org/abs/1706.03762
- **An Image is Worth 16x16 Words**, Dosovitskiy et al., 2020 — https://arxiv.org/abs/2010.11929

它们用于离线验证 section、figure、table、equation、ZIP 安全边界和资产优先级。运行 `python tests/fixtures/build_fixtures.py` 可确定性重建 `paper.pdf`、`source.zip` 与 raster 测试图。

