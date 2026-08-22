# Changelog folder / 更改日志目录

Where the team records what it did. Two kinds of record live here, and they answer different
questions.

| File | Answers | Who writes it |
| --- | --- | --- |
| [`CHANGELOG.md`](CHANGELOG.md) | What changed in the product, and why it mattered | Everyone |
| [`work-packages/`](work-packages/) | How one piece of work was carried out, from which baseline, within what scope | Whoever owns that track |

## Which one does my entry go in?

Ask what your reader wants to know.

- **Something about the product is now different** — a new endpoint, a fixed defect, a changed
  contract, a deployment that behaves differently. That belongs in `CHANGELOG.md`, under the
  section matching the area, whichever track did the work.
- **A piece of work opened, progressed, or closed** — a baseline recorded, a scope declared, a
  limitation confirmed and deliberately left open. That belongs in a work-package file, even
  when it changed no code at all.

Plenty of work produces both. Write both; they are not duplicates, because they answer
different questions.

## Conventions

- Bilingual, English first then 简体中文, as a pair of lines per entry. It matches the rest of
  the repository's documentation.
- Say **why**, not only what. The diff already records what changed; it cannot record the
  reason, and the reason is what a reader six weeks later actually needs.
- One work-package file per track, named for the track rather than the person, so the file
  survives whoever hands it over: `work-packages/crypto-track.md`. Start a new one by copying
  the header of an existing file.
- Nothing here is generated. If an entry is wrong, correct it in place.

## History

This folder replaces `CT_Logs/`, which was named for one track but had become the project's
only changelog. `git log --follow` traces both files back through the move.

---

# 更改日志目录

团队记录做过什么的地方。这里存放两类记录，它们回答的是不同的问题。

| 文件 | 回答什么 | 由谁写 |
| --- | --- | --- |
| [`CHANGELOG.md`](CHANGELOG.md) | 产品发生了什么变化，以及为什么重要 | 所有人 |
| [`work-packages/`](work-packages/) | 某一块工作是怎么推进的：基线是什么、范围到哪里 | 该条线的负责人 |

## 我的记录该写进哪一份？

想一想读者想知道的是什么。

- **产品现在不一样了**——新增端点、修好的缺陷、变更的契约、行为不同的部署。写进 `CHANGELOG.md`
  对应领域的小节，无论这项工作出自哪条线。
- **某块工作开始、推进或收尾了**——记录了基线、声明了范围、确认了某个有意保留的限制。写进对应的
  工作包文件，即使它没有改动任何代码。

很多工作两边都要写。请两边都写——它们不是重复，因为回答的是不同的问题。

## 约定

- 双语，英文在前、简体中文在后，每条成对出现，与仓库其余文档保持一致。
- 写清楚**为什么**，而不只是改了什么。diff 已经记录了改动本身，却记录不了当时的理由，而理由正是
  六周后的读者真正需要的东西。
- 每条线一个工作包文件，以**线**命名而非以人命名，这样交接之后文件依然成立：
  `work-packages/crypto-track.md`。新开一条线时，复制现有文件的头部即可。
- 这里没有任何自动生成的内容。条目写错了就地改正。

## 沿革

本目录取代了 `CT_Logs/`——那个目录以某一条线命名，却实际上成了整个项目唯一的更改日志。两个文件
都可以用 `git log --follow` 追溯到迁移之前。
