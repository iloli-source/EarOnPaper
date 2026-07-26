正在用 X 实时搜索相关话题，覆盖网易/腾讯/字节音乐 AI、多基频估计、吉他谱生成与 MuScriptor。继续深挖多基频论文、吉他谱生成，以及中文圈对 MuScriptor / 大厂音乐 AI 的讨论。# 2026 扒谱 / 自动采谱 AI：X 实时检索纪要

检索时间约 **2026-07-26**。结论先说：**真正「混音→分轨 MIDI」的热点几乎被 MuScriptor 吃满**；国内大厂帖子多是 **AI 作曲/平台生态**，不是 AMT 论文；吉他谱侧是 **Songsterr AI + FretBench 评测**，学术向多基频帖偏少。

---

## 1. MuScriptor（当前最硬核 · 多乐器 Audio→MIDI）

### 官方发布（必读）

| 账号 | 日期 | 链接 | 要点 |
|------|------|------|------|
| [@kyutai_labs](https://x.com/kyutai_labs) | 2026-07-10 | [主帖](https://x.com/kyutai_labs/status/2075540047613276197) | 与 [@MireloAI](https://x.com/MireloAI) 合作开源；声称当前 **最强开源多乐器转录**；任意类型混音可出 **分乐器 MIDI**；约 **12.8 万赞 / 29.8 万浏览** |
| 同上 | 同串 | [数据帖](https://x.com/kyutai_labs/status/2075540049337155964) | 瓶颈是数据：自 MT3(2022) 以来缺真数据；收集 **17 万条录音 / 约 1.1 万小时**，带 MIDI 对齐 |
| 同上 | 同串 | [架构帖](https://x.com/kyutai_labs/status/2075540050930991170) | **Decoder-only Transformer**；5 秒 mel → MT3 风格 token；长音频分块；规模 **100M–1.3B** |
| 同上 | 同串 | [训练帖](https://x.com/kyutai_labs/status/2075540052700954997) | 合成预训 **150 万 MIDI** → 真实数据微调 → **RL 后训**（300 首人工校验谱） |
| 同上 | 同串 | [资源帖](https://x.com/kyutai_labs/status/2075540054261305499) | Demo：https://muscriptor.kyutai.org · Code：https://github.com/muscriptor/muscriptor · Paper：https://arxiv.org/abs/2607.08168 |

### API / 生态

| 账号 | 日期 | 链接 | 要点 |
|------|------|------|------|
| [@MireloAI](https://x.com/MireloAI) | 2026-07-23 | [帖子](https://x.com/MireloAI/status/2080342247418048750) | 开源 3 档速度/质量模型；**最佳版上 API**（最高精度、免自托管）；开源本地版继续维护；约 **270 赞 / 1.9 万浏览** |
| [@cjsimongabriel](https://x.com/cjsimongabriel) | 2026-07-23 | [帖子](https://x.com/cjsimongabriel/status/2080348718566367570) | 官方联合发布人：API 版比开源更好，欢迎试用 |
| [@jtydhr88](https://x.com/jtydhr88) | 2026-07-26 | [帖子](https://x.com/jtydhr88/status/2081202247703134482) | **ComfyUI-muscriptor** 自定义节点：https://github.com/jtydhr88/ComfyUI-muscriptor |

### 中文 / 日文「报告向」帖（更接近你要的中文解读）

| 账号 | 语言 | 链接 | 要点 |
|------|------|------|------|
| [@AINativeF_zh](https://x.com/AINativeF_zh) **AI 原生基金会** | **中文** | [帖子](https://x.com/AINativeF_zh/status/2077541569843146967) | 标题直译：**「MuScriptor：多乐器音乐转录开放模型」**；关键词：AMT / 合成数据 / RL；目标=改善真实多乐器场景；方法=合成预训+真实微调+RL+乐器条件 |
| [@ai_hakase_](https://x.com/ai_hakase_) | 日文长文 | [帖子](https://x.com/ai_hakase_/status/2076895214392824152) | 多乐器同时 MIDI；BPM/Key/和弦；量化导出进 DAW；Auto/Custom 模式（指定乐器提精度）；约 **252 赞 / 1.7 万浏览** |
| [@AIMIRAI46487](https://x.com/AIMIRAI46487) | 日文简讯 | [帖子](https://x.com/AIMIRAI46487/status/2080494315017802092) | 转述 Mirelo **API 发布** |
| [@regonn_curry](https://x.com/regonn_curry) | 日语播客 | [帖子](https://x.com/regonn_curry/status/2080897687709454468) | 播客 #353 专门聊 MuScriptor（同集还有 Gemini Spark、Kimi K3） |

### 用户实测（真反馈）

| 账号 | 链接 | 要点 |
|------|------|------|
| [@grmchn4ai](https://x.com/grmchn4ai) | [帖子](https://x.com/grmchn4ai/status/2076190087017324581) | 本地实测复杂 **DnB+人声** 也能抓；发 demo 视频；曾搭临时服务器让人拖拽试；**536 赞 / 10.9 万浏览** |
| [@mameshiba______](https://x.com/mameshiba______) | [帖子](https://x.com/mameshiba______/status/2079609494930415780) | 自写 Audio→MIDI App：**实用级精度，冲击感强** |
| [@Qto6BshdBJYXdch](https://x.com/Qto6BshdBJYXdch) | [帖子](https://x.com/Qto6BshdBJYXdch/status/2079873511284416967) | 「近年最感动 AI」；精度高到「令和着メロ工全失业」段子 |
| [@Sub_Cha_Sub](https://x.com/Sub_Cha_Sub) | [帖子](https://x.com/Sub_Cha_Sub/status/2080868304722506056) | 整体不错，**钢琴 MIDI 仍遗憾** |
| [@kaki_GT](https://x.com/kaki_GT) | [帖子](https://x.com/kaki_GT/status/2079552514689806661) | 弦乐也能出 MIDI；**先 stem 再单轨转录更准**；适合分析句型而非纯替代耳朵 |
| [@2zn01v](https://x.com/2zn01v) | [帖子](https://x.com/2zn01v/status/2079554048135704732) | 自研采谱：MuScriptor + **Basic Pitch**（力度/弯音）+ **ISMIR2019 和弦** 综合取优 |
| [@sonic_field](https://x.com/sonic_field) | [帖子](https://x.com/sonic_field/status/2078880397920731383) | 技术拆解：5 秒谱图 token 含时间/乐器/音高/起止；长文 https://sonicfield.org/muscriptor-audio-to-midi |
| [@vplandtweets](https://x.com/vplandtweets) | [帖子](https://x.com/vplandtweets/status/2079960322295640359) | 核心价值是 **分轨可编辑 MIDI**（换音色、改和弦、抽贝斯线） |

**一句话**：2026 年 7 月，X 上「自动扒谱」主叙事 = **Kyutai × Mirelo 的 MuScriptor（论文 arXiv:2607.08168）**，中文深度长文仍少，但 **@AINativeF_zh 有结构化中文摘要**。

---

## 2. 「多基频 / 多乐器估计」与相关论文线索

在 X 上 **几乎没有** 独立刷屏的「纯 multipitch estimation 新论文」；讨论多被 MuScriptor 覆盖。能落到实链的：

| 来源 | 链接 | 要点 |
|------|------|------|
| Kyutai 主帖 + 论文 | [主帖](https://x.com/kyutai_labs/status/2075540047613276197) · [arXiv](https://arxiv.org/abs/2607.08168) | 不是传统帧级 multipitch 谱，而是 **多乐器、结构化 MIDI token 生成**（MT3 路线的扩展） |
| 训练叙事 | [数据](https://x.com/kyutai_labs/status/2075540049337155964) / [训练](https://x.com/kyutai_labs/status/2075540052700954997) | 明确对标 **MT3 (2022)** 的数据瓶颈；合成→真实→RL 三阶段 |
| 和弦识别组件 | [@knoike](https://x.com/knoike) [帖](https://x.com/knoike/status/2080770473718411743) | 引用 **ISMIR 2019 Large-Vocabulary Chord Recognition**：https://github.com/music-x-lab/ISMIR2019-Large-Vocabulary-Chord-Recognition |
| 工程拼装 | [@2zn01v](https://x.com/2zn01v) [帖](https://x.com/2zn01v/status/2079554048135704732) | **MuScriptor + Basic Pitch + 和弦模型** 多源融合——更像「生产向 multipitch 管线」而非单篇论文 |

**诚实边界**：X 实时流里 **难找 2026 新 arXiv multipitch 论文的中文刷屏帖**；若要学术扫 arXiv，需另做 Web/arXiv 检索，不能用 X 冒充论文库。

---

## 3. 吉他谱 / Tab 生成与评测

| 账号 | 日期 | 链接 | 要点 |
|------|------|------|------|
| [@JaidenCapra](https://x.com/JaidenCapra) | 2026-03 | [帖子](https://x.com/JaidenCapra/status/2030826324735201425) | 开源评测 **FretBench**：测 LLM **读吉他谱**能力；多数模型不行，最差 **低于随机**；https://fretbench.tymo.ai/ |
| [@dadabots](https://x.com/dadabots) | 2026-01 | [帖子](https://x.com/dadabots/status/2012004055351193820) | Tab 需专用模型；ASCII tab token 差；手握 **20 万 Guitar Pro 压缩序列**；更看好 discrete diffusion |
| [@staple8185](https://x.com/staple8185) | 2025-12 | [帖子](https://x.com/staple8185/status/2000763434158448736) | **Songsterr 付费 AI 读谱**→可 PC 校正；精度一般，**不如 Guitar Pro**，初中级可用 |
| [@TFCAguia](https://x.com/TFCAguia) | 2026-07 | [帖子](https://x.com/TFCAguia/status/2080502208081150132) | 吐槽 Songsterr：**新谱大量 AI 垃圾**，且不再标 AI 标识 |
| [@GadiBorovich](https://x.com/GadiBorovich) | 2026-04 | [帖子](https://x.com/GadiBorovich/status/2049517764457717810) | 创业者用 **380 小时音频训吉他转录模型**（个案，非开源爆款） |
| [@xrock_y](https://x.com/xrock_y) | 2026-07 | [帖子](https://x.com/xrock_y/status/2080666838250516735) | 练习日志提到 **Songsterr AI 公开** |

**结论**：吉他侧 X 热度 = **商业 Songsterr AI（质量争议大）** + **FretBench 证明「读谱」仍难** + **Guitar Pro 数据/格式仍是专业标准**；尚未出现像 MuScriptor 那样统一的「音频→六线谱」开源霸主帖。

---

## 4. 网易 / 腾讯 / 字节：音乐 AI（生成向，非扒谱）

X 中文圈 **几乎没有**「三大厂发布自动采谱模型」的硬帖；可见内容偏 **生成与平台**：

| 账号 | 链接 | 与谁相关 | 要点 |
|------|------|----------|------|
| [@_miuj_9](https://x.com/_miuj_9) | [帖子](https://x.com/_miuj_9/status/2079916397434720543) | **网易云** | AI 写歌大赛：冠/亚/季 **30/20/15 万**；投稿可用 **乐评喂 AI 写歌** |
| [@Arctique4](https://x.com/Arctique4) | [帖子](https://x.com/Arctique4/status/2074181643460612605) | **字节·汽水音乐** | 「汽水里很多 AI 作曲，灾难，好的太少」 |
| [@onehajimi](https://x.com/onehajimi) | [帖子](https://x.com/onehajimi/status/2080233057303310567) | 对照网易/QQ | Deezer 日增约一半 AI 歌 → 对国内曲库同质化的感慨 |
| [@CryptoSunova](https://x.com/CryptoSunova) | [帖子](https://x.com/CryptoSunova/status/2062902848648856050) | **网易云分发** | 自己旋律+词，**AI 用自己声音唱+混**，发网易云 |
| [@hrichina](https://x.com/hrichina) | [帖子](https://x.com/hrichina/status/2079479121713721488) | 监管旁证 | 提及网易云 **「妙时」** 等拟人 AI 下线（情感陪伴监管，非扒谱） |
| [@AndoRAG](https://x.com/AndoRAG) | [帖子](https://x.com/AndoRAG/status/2080556699577164156) | **字节命名** | 汽水音乐等「具象名词」产品策略 |

**结论**：三大厂在 X 上的 2026 叙事是 **AI 作曲/分发/大赛/伴聊下线**，**不是 multipitch / 自动谱面研究**。若你要厂内 AMT，需微博/知乎/公众号/论文库另搜。

---

## 5. 扒谱前置：分轨工具（中文高传播）

| 账号 | 链接 | 要点 |
|------|------|------|
| [@XAMTO_AI](https://x.com/XAMTO_AI) | [帖子](https://x.com/XAMTO_AI/status/2061030928986878151) | **StemDeck**：本地 Demucs，拆 **人声/鼓/贝斯/吉他/钢琴/其他**；BPM/调性；**4093 赞 / 23 万浏览** |
| [@GitHub_Daily](https://x.com/GitHub_Daily) | [帖子](https://x.com/GitHub_Daily/status/2069050301651579256) | 中文再推 StemDeck：https://github.com/stemdeckapp/stemdeck；六轨+混音器；Win/Mac |
| [@0xCheshire](https://x.com/0xCheshire) | [帖子](https://x.com/0xCheshire/status/2080210814984994975) | **ACE-Step 1.5** 本地音乐生成：分轨/多轨/翻唱/重绘；&lt;4GB 显存（偏生成，非采谱） |

实用流水线（社区共识）：**StemDeck/Demucs 分轨 → MuScriptor 转 MIDI →（吉他）Guitar Pro / Songsterr 人工修**。

---

## 6. 快速地图（2026-07）

```
混音音频
   ├─ 分轨  → StemDeck / Demucs
   ├─ 多乐器 MIDI → MuScriptor (Kyutai+Mirelo) ★主线
   │      + Basic Pitch 力度/弯音
   │      + 和弦模型 (ISMIR'19 等)
   ├─ 吉他 Tab  → Songsterr AI（争议）/ Guitar Pro 人工
   └─ 国内大厂  → 主要是 AI 写歌/平台，非 AMT 开源
```

---

## 7. 检索局限（透明说明）

1. **中文长文 MuScriptor**：有 **@AINativeF_zh 结构化摘要**，但刷屏级中文教程仍少于日/英。  
2. **「多基频估计新论文」**：X 实时流几乎被 MuScriptor 替代；独立 multipitch arXiv 帖稀少。  
3. **网易/腾讯/字节采谱模型**：本次关键词+语义检索 **未命中官方 AMT 发布帖**。  
4. 帖子链接格式：`https://x.com/{user}/status/{id}`，均可点开核对原文。

若需要下一轮，可指定：**只扫 arXiv 2025–2026 multipitch**、或 **只跟中文 MuScriptor 复现教程**、或 **Songsterr AI vs MuScriptor 吉他可用度对比实测帖**。
