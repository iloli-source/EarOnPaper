----------------------------- MODULE StemCache -----------------------------
(* 追加形式エクスポート（export-extra）が使う採譜済み MusicXML キャッシュ
   （primaryMusicxmlByInput）と、レンダラ側の楽器別結果キャッシュ（stemResults）の
   食い違いの最小モデル。入力は1つ。採譜はレンダラが直列化するので各操作は原子的。
   KeyByInstrument = FALSE: 修正前。メイン側キャッシュは入力だけがキー（最後に採譜した楽器）。
   KeyByInstrument = TRUE : 修正後。(入力, 楽器) がキーで、export-extra は表示中の楽器を渡す。 *)
CONSTANTS Instruments, KeyByInstrument

VARIABLES rendered,   \* レンダラの stemResults にある楽器
          selected,   \* 画面で選択中の楽器（"none" = 未選択）
          lastXml,    \* 修正前キャッシュ: 最後に採譜した楽器の MusicXML
          xmlByStem,  \* 修正後キャッシュ: MusicXML を持つ楽器の集合
          exported    \* 直近の export-extra: [want |-> 表示中の楽器, src |-> 使った MusicXML の楽器]
vars == <<rendered, selected, lastXml, xmlByStem, exported>>

Maybe == Instruments \cup {"none"}

TypeOK ==
  /\ rendered \subseteq Instruments
  /\ selected \in Maybe
  /\ lastXml \in Maybe
  /\ xmlByStem \subseteq Instruments
  /\ exported \in [want : Maybe, src : Maybe \cup {"fallback"}]

Init ==
  /\ rendered = {} /\ selected = "none" /\ lastXml = "none" /\ xmlByStem = {}
  /\ exported = [want |-> "none", src |-> "none"]

\* 未採譜の楽器を選ぶ: transcribe-stem が走り、メイン側キャッシュも更新される
Transcribe(i) ==
  /\ i \notin rendered
  /\ rendered' = rendered \cup {i} /\ selected' = i
  /\ lastXml' = i /\ xmlByStem' = xmlByStem \cup {i}
  /\ UNCHANGED exported

\* 採譜済みの楽器へ切り替える: レンダラのキャッシュから即表示し、メインは呼ばれない
Switch(i) ==
  /\ i \in rendered /\ i # selected
  /\ selected' = i
  /\ UNCHANGED <<rendered, lastXml, xmlByStem, exported>>

\* 追加形式を出力する。キャッシュに無ければ音声からの再採譜へフォールバックする
Export ==
  /\ selected # "none"
  /\ exported' = [want |-> selected,
                  src |-> IF KeyByInstrument
                            THEN (IF selected \in xmlByStem THEN selected ELSE "fallback")
                            ELSE lastXml]
  /\ UNCHANGED <<rendered, selected, lastXml, xmlByStem>>

Next == (\E i \in Instruments : Transcribe(i) \/ Switch(i)) \/ Export
Spec == Init /\ [][Next]_vars

\* 追加形式は、表示中の楽器の採譜結果から作られる
CacheKeyMatchesInstrument == exported.want = exported.src
=============================================================================
