```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	Igestor(Igestor)
	classifier(classifier)
	__end__([<p>__end__</p>]):::last
	Igestor --> classifier;
	__start__ --> Igestor;
	classifier --> __end__;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc

```