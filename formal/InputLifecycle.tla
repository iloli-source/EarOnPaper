--------------------------- MODULE InputLifecycle ---------------------------
(* app/main.js の transcribe / transcribe-stem ハンドラ（H）と、release-input・
   cleanupAllResources（ウィンドウ close / before-quit）の競合の最小モデル。入力は1つ。
   Node のイベントループは単一スレッドなので、割り込みは await 点でしか起きない。
   ハンドラの await 点は「エンジン子プロセスの終了待ち」と「終了後の任意成果物 stat」の2つ。
   Guard = FALSE: 修正前。await 後に世代を再確認せず primaryMusicxml キャッシュへ公開する。
                  release は kill 待ちの await 中に始まった子プロセスを止めない。
   Guard = TRUE : 修正後。開始時に捕まえた世代を公開直前に再確認し、release は
                  kill 待ちの後に残った子プロセスが無くなるまで止め直す。 *)
EXTENDS Naturals, FiniteSets

CONSTANTS Handlers,      \* 同一入力に対するハンドラ呼び出し
          Guard,         \* 世代ガード + release の止め直し
          Invalidators,  \* 有効にする無効化操作: "release" / "cleanup" の部分集合
          MaxInv         \* 無効化操作の回数上限（状態空間の有界化）

VARIABLES pc,        \* h -> "idle" | "engine" | "killed" | "ensured" | "done" | "failed"
          rootLive,  \* h -> 出力用一時ディレクトリが実在するか
          hgen,      \* h -> 開始時に捕まえた世代
          gen,       \* 入力の世代（release / cleanup で進む）
          cache,     \* primaryMusicxmlByInput の指す先: "none" またはハンドラ
          rel,       \* release-input: "idle" | "waiting"（kill した子の close 待ち）
          inv        \* 実行した無効化操作の回数
vars == <<pc, rootLive, hgen, gen, cache, rel, inv>>

PcStates == {"idle", "engine", "killed", "ensured", "done", "failed"}

TypeOK ==
  /\ pc \in [Handlers -> PcStates]
  /\ rootLive \in [Handlers -> BOOLEAN]
  /\ hgen \in [Handlers -> Nat]
  /\ gen \in Nat
  /\ cache \in Handlers \cup {"none"}
  /\ rel \in {"idle", "waiting"}
  /\ inv \in 0..MaxInv

Init ==
  /\ pc = [h \in Handlers |-> "idle"]
  /\ rootLive = [h \in Handlers |-> FALSE]
  /\ hgen = [h \in Handlers |-> 0]
  /\ gen = 0 /\ cache = "none" /\ rel = "idle" /\ inv = 0

Bump == IF Guard THEN gen + 1 ELSE gen

\* ハンドラ開始: mkdtemp + registerRoot + spawn までは同期。世代もここで捕まえる
Start(h) ==
  /\ pc[h] = "idle"
  /\ pc' = [pc EXCEPT ![h] = "engine"]
  /\ rootLive' = [rootLive EXCEPT ![h] = TRUE]
  /\ hgen' = [hgen EXCEPT ![h] = gen]
  /\ UNCHANGED <<gen, cache, rel, inv>>

\* 子プロセスが exit 0。必須成果物の stat（ensureOutputs）は出力先が消えていれば失敗し、
\* catch で removeRoot する。通れば任意成果物の stat（await）へ進む
EngineExit(h) ==
  /\ pc[h] = "engine"
  /\ pc' = [pc EXCEPT ![h] = IF rootLive[h] THEN "ensured" ELSE "failed"]
  /\ UNCHANGED <<rootLive, hgen, gen, cache, rel, inv>>

\* kill された子プロセスの close がハンドラへ届く: reject -> catch -> removeRoot
Close(h) ==
  /\ pc[h] = "killed"
  /\ pc' = [pc EXCEPT ![h] = "failed"]
  /\ rootLive' = [rootLive EXCEPT ![h] = FALSE]
  /\ UNCHANGED <<hgen, gen, cache, rel, inv>>

\* 任意成果物の stat から復帰して公開する。修正後は世代が変わっていれば破棄（removeRoot）
Publish(h) ==
  /\ pc[h] = "ensured"
  /\ IF Guard /\ hgen[h] # gen
       THEN /\ pc' = [pc EXCEPT ![h] = "failed"]
            /\ rootLive' = [rootLive EXCEPT ![h] = FALSE]
            /\ cache' = cache
       ELSE /\ pc' = [pc EXCEPT ![h] = "done"]
            /\ cache' = h
            /\ rootLive' = rootLive
  /\ UNCHANGED <<hgen, gen, rel, inv>>

Running == {h \in Handlers : pc[h] = "engine"}
Dying == {h \in Handlers : pc[h] = "killed"}
AllRootsGone == [h \in Handlers |-> FALSE]

\* release-input: 実行中の子が無ければ await 無しで同期的に解放する
ReleaseSync ==
  /\ "release" \in Invalidators /\ rel = "idle" /\ inv < MaxInv
  /\ Running = {} /\ Dying = {}
  /\ rootLive' = AllRootsGone /\ cache' = "none"
  /\ gen' = Bump /\ inv' = inv + 1
  /\ UNCHANGED <<pc, hgen, rel>>

\* release-input: 実行中の子を kill して close を待つ（ここが await 点）
ReleaseKill ==
  /\ "release" \in Invalidators /\ rel = "idle" /\ inv < MaxInv
  /\ Running # {}
  /\ pc' = [h \in Handlers |-> IF h \in Running THEN "killed" ELSE pc[h]]
  /\ rel' = "waiting" /\ gen' = Bump /\ inv' = inv + 1
  /\ UNCHANGED <<rootLive, hgen, cache>>

\* close 待ちから復帰してルートを削除する。修正後は待機中に始まった子が残っていれば
\* もう一度 kill して待ち直す（削除はしない）
ReleaseFinish ==
  /\ rel = "waiting" /\ Dying = {}
  /\ IF Guard /\ Running # {}
       THEN /\ pc' = [h \in Handlers |-> IF h \in Running THEN "killed" ELSE pc[h]]
            /\ gen' = Bump
            /\ UNCHANGED <<rootLive, cache, rel>>
       ELSE /\ rootLive' = AllRootsGone /\ cache' = "none"
            /\ rel' = "idle" /\ gen' = Bump
            /\ pc' = pc
  /\ UNCHANGED <<hgen, inv>>

\* cleanupAllResources: await 無し。kill を送り（close は後から届く）全ルートを即削除する
Cleanup ==
  /\ "cleanup" \in Invalidators /\ rel = "idle" /\ inv < MaxInv
  /\ pc' = [h \in Handlers |-> IF h \in Running THEN "killed" ELSE pc[h]]
  /\ rootLive' = AllRootsGone /\ cache' = "none"
  /\ gen' = Bump /\ inv' = inv + 1
  /\ UNCHANGED <<hgen, rel>>

Next ==
  \/ \E h \in Handlers : Start(h) \/ EngineExit(h) \/ Close(h) \/ Publish(h)
  \/ ReleaseSync \/ ReleaseKill \/ ReleaseFinish \/ Cleanup
Spec == Init /\ [][Next]_vars

\* キャッシュは実在する出力ルートだけを指す（解放済みの結果を公開しない）
NoPublishAfterRelease == cache # "none" => rootLive[cache]

\* 出力先を消された子プロセスが動き続けない（release 完了後に孤児を残さない）
NoOrphanEngine == \A h \in Handlers : pc[h] = "engine" => rootLive[h]
=============================================================================
