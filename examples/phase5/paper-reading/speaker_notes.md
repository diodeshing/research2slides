# Speaker Notes: 注意力序列建模：测试样例讲解

## Slide 1: 序列建模需求推动 Attention 成为架构核心

### Purpose

先说明序列建模需求，再引出架构设计。

### Main Message

序列建模需求推动架构将注意力机制（Attention）作为核心运算。

### Speaking Script

这一页先明确问题背景。样例关注 Sequence Modeling，并把 Attention 放在架构的核心位置。这里先解释设计动机，不提前展开公式。

### Visual Guidance

采用简洁的文字布局，按问题背景和设计方向依次讲解。

### Transition

理解问题背景以后，下一页看 Query、Key 与 Value 如何交互。

### Estimated Time

55 seconds

## Slide 2: 注意力机制通过 Query、Key 与 Value 建立信息交互

### Purpose

结合原始架构图解释 Attention 的核心交互。

### Main Message

注意力模块通过查询（Query）、键（Key）和值（Value）建立信息交互。

### Speaking Script

这一页先看整体交互，不展开公式。Query 表示当前希望查找的信息，Key 用于完成匹配，Value 则提供最终需要聚合的内容。原图中的 Encoder、Decoder 等标签保持英文。

### Visual Guidance

先指向原始 Figure，再用一个中文标注强调 Attention 连接。

### Transition

明确 Q、K、V 的角色以后，下一页进一步看 Attention Equation。

### Estimated Time

65 seconds

## Slide 3: Attention 通过 Query-Key 匹配实现 Value 加权聚合

### Purpose

用原始公式解释 Query-Key 匹配和 Value 聚合。

### Main Message

样例将注意力计算写为 Attention(Q,K,V)=softmax(QK^T)V。

### Speaking Script

公式分两步理解。首先，QK^T 计算 Query 与 Key 的匹配得分。随后，Softmax 把得分归一化为权重，并用这些权重对 Value 进行聚合。

### Visual Guidance

沿公式从左到右讲解，不重绘也不翻译数学符号。

### Transition

理解计算过程以后，下一页查看 fixture 中唯一的量化比较。

### Estimated Time

80 seconds

## Slide 4: 样例模型得分为 11.0，高于基线的 10.0

### Purpose

展示量化比较，同时保留软件测试免责声明。

### Main Message

样例模型得分为 11.0，高于基线的 10.0。

### Speaking Script

表格保留 Fixture baseline 和 Fixture model 的英文名称。数值分别为 10.0 和 11.0，但它们只是测试数据，用于检查表格、引用和渲染流程。

### Visual Guidance

使用可编辑表格，中文化通用表头，并保留模型名称和数值。

### Transition

下一页直接说明为什么这组数字不能支持科研结论。

### Estimated Time

65 seconds

## Slide 5: 测试数据只能验证软件流程，不能支持科研结论

### Purpose

防止听众把 fixture 数值误解为科研证据。

### Main Message

结果数值仅为软件测试而构造，不能支持科研结论。

### Speaking Script

这里必须把证据边界说清楚。10.0 和 11.0 用于验证 parsing、evidence mapping 与 slide pipeline，不能作为论文实验结果引用。

### Visual Guidance

保留充足留白，用两行中文直接说明测试用途和科研边界。

### Transition

最后只总结 fixture 真正支持的 Attention 交互机制。

### Estimated Time

40 seconds

## Slide 6: Attention 通过 Query-Key-Value 完成信息交互

### Purpose

以证据支持的概念结论结束汇报。

### Main Message

样例支持 Attention 的信息交互机制，测试分数不构成科研结论。

### Speaking Script

收尾只保留有证据支持的内容。Attention 根据 Query 与 Key 的匹配关系选择并聚合 Value，前面的 10.0 和 11.0 不进入科研结论。

### Visual Guidance

保持结尾页简洁，突出一条中文核心结论。

### Transition

结束汇报。

### Estimated Time

40 seconds

## Estimated Total Presentation Time

345 seconds (5.8 minutes)
