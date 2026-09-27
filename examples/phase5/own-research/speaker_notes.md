# Speaker Notes: 我们的注意力序列建模测试样例

## Slide 1: 序列建模需求推动 Attention 成为设计核心

### Purpose

说明推动我们进行架构设计的序列建模问题。

### Main Message

序列建模需求推动架构将注意力机制（Attention）作为核心运算。

### Speaking Script

先说明我们处理的是 Sequence Modeling 问题。这个需求决定了当前设计把 Attention 放在核心位置，本页只交代动机和设计方向。

### Visual Guidance

使用克制的文字布局，先讲问题，再讲设计方向。

### Transition

接下来说明我们的核心信息交互方式。

### Estimated Time

50 seconds

## Slide 2: 我们的样例通过 Attention 连接 Query、Key 与 Value

### Purpose

结合原始架构图说明当前样例支持的研究思路。

### Main Message

我们的样例通过 Attention 连接 Query、Key 与 Value。

### Speaking Script

这一页说明样例当前强调什么。Query 表示信息需求，Key 用于匹配，Value 提供需要聚合的内容。原始 Figure 中的 Encoder 与 Decoder 等标签保持英文。

### Visual Guidance

让原始 Figure 成为主要视觉，只增加一处中文解释。

### Transition

下一页用 Attention Equation 解释这一交互。

### Estimated Time

60 seconds

## Slide 3: Attention 通过 Query-Key 匹配实现 Value 加权聚合

### Purpose

解释样例方法的数学形式。

### Main Message

样例将注意力计算写为 Attention(Q,K,V)=softmax(QK^T)V。

### Speaking Script

公式从左到右解释。QK^T 形成匹配得分，Softmax 将得分转换为权重，最后这些权重作用在 V 上完成信息聚合。

### Visual Guidance

使用原始公式作为唯一主要视觉，按讲解顺序突出各部分。

### Transition

理解方法以后，下一页查看当前量化结果。

### Estimated Time

80 seconds

## Slide 4: 样例模型得分为 11.0，高于基线的 10.0

### Purpose

按原始精度呈现现有 fixture 比较。

### Main Message

样例模型得分为 11.0，高于基线的 10.0。

### Speaking Script

这里只报告已有数值。Fixture baseline 为 10.0，Fixture model 为 11.0。我们不增加百分比，也不把它解释成真实科研提升。

### Visual Guidance

使用可编辑表格，中文化通用表头，同时保留模型名称与数值。

### Transition

下一页说明为什么这组结果不能支持科研结论。

### Estimated Time

60 seconds

## Slide 5: 测试数据只能验证软件流程，不能支持科研结论

### Purpose

直接说明当前证据的限制。

### Main Message

结果数值仅为软件测试而构造，不能支持科研结论。

### Speaking Script

这一限制必须直接说明。数值只验证 pipeline 能否正确处理 table、claim 和 citation，不验证我们的研究方法。

### Visual Guidance

采用最小化文字布局，不添加装饰性警告图标。

### Transition

最后总结当前真正得到支持的结论。

### Estimated Time

40 seconds

## Slide 6: Attention 通过 Query-Key-Value 完成信息交互

### Purpose

用证据支持的概念结论结束汇报。

### Main Message

样例支持 Attention 的信息交互机制，测试分数不构成科研结论。

### Speaking Script

结论只保留证据支持的内容，也就是 Attention 对 Query、Key 与 Value 的连接。测试分数只用于软件验收，不进入我们的科研结论。

### Visual Guidance

突出一条结论，并用一行文字说明证据边界。

### Transition

结束汇报。

### Estimated Time

40 seconds

## Estimated Total Presentation Time

330 seconds (5.5 minutes)
