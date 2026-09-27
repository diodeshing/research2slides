# Speaker Notes: Our Attention-based Sequence Modeling Fixture

## Slide 1: Sequence modeling motivates an attention-centered architecture

### Purpose

Frame the sequence-modeling problem that motivates our fixture design.

### Main Message

Sequence modeling motivates an architecture centered on attention operations.

### Speaking Script

先说明我们处理的 context 是 sequence modeling。这个需求决定了后续设计把 attention operations 放在核心位置。

### Visual Guidance

Use a restrained text composition with the problem and design direction aligned vertically.

### Transition

接下来说明我们的核心 interaction。

### Estimated Time

50 seconds

## Slide 2: Our fixture connects queries, keys, and values

### Purpose

Present the supported contribution using the source architecture figure.

### Main Message

Our fixture connects queries, keys, and values through attention.

### Speaking Script

这一页说明我们的 fixture 强调什么。先看 source figure，再沿 attention connection 解释 query、key 和 value 的关系。

### Visual Guidance

Let the original source figure dominate the slide and keep annotation to one highlight.

### Transition

下面用公式解释这个 interaction。

### Estimated Time

60 seconds

## Slide 3: Attention combines query-key scores with values

### Purpose

Explain the mathematical form of the fixture method.

### Main Message

The fixture defines attention as Attention(Q,K,V)=softmax(QK^T)V.

### Speaking Script

公式从左到右解释。QK^T 形成 matching scores，softmax 把分数转为权重，最后这些权重作用在 V 上。

### Visual Guidance

Use the source equation as the only primary visual and highlight each term in speaking order.

### Transition

理解方法以后，看现有的量化结果。

### Estimated Time

80 seconds

## Slide 4: The fixture model scores 11.0 versus 10.0

### Purpose

Present the available fixture comparison with its original precision.

### Main Message

The fixture model scores 11.0 versus 10.0 for the fixture baseline.

### Speaking Script

这里只报告已有数值。baseline 是 10.0，fixture model 是 11.0。我们不增加百分比，也不把它解释成真实科研提升。

### Visual Guidance

Render an editable two-row table and preserve labels and precision.

### Transition

下一页说明为什么这个结果不能支持科研结论。

### Estimated Time

60 seconds

## Slide 5: Fixture values cannot support a scientific conclusion

### Purpose

State the evidence limitation candidly.

### Main Message

The result values are invented solely for software testing.

### Speaking Script

这一限制必须直接说明。数值只验证 pipeline 是否能处理 table、claim 和 citation，不验证我们的研究方法。

### Visual Guidance

Use a minimal text slide with strong hierarchy and no decorative warning graphic.

### Transition

最后总结当前真正得到支持的结论。

### Estimated Time

40 seconds

## Slide 6: Attention links queries, keys, and values

### Purpose

Conclude with the evidence-supported concept.

### Main Message

The fixture links attention to queries, keys, and values.

### Speaking Script

结论只保留证据支持的内容，也就是 attention 对 query、key 和 value 的连接。测试分数不进入我们的科研结论。

### Visual Guidance

Use one conclusion sentence and one short evidence boundary statement.

### Transition

End the presentation.

### Estimated Time

40 seconds

## Estimated Total Presentation Time

330 seconds (5.5 minutes)
