-------------------------- MODULE SeparationOwner --------------------------
(* 同一入力に対する separate-audio の2呼び出し（先行 A・後続 B）と separationCache の
   所有者の最小モデル。A の失敗経路（catch）はキャッシュを削除する。
   通常経路では B 冒頭の releaseInputResources が A の子プロセスを kill して close を
   待つため、A の catch は必ず B のキャッシュ登録より前に走る。
   cleanupAllResources は activeProcesses を待たずに空にするので、その後の B は A の
   close を待てず、A の catch が B の登録後に走り得る。
   OwnerCheck = FALSE: 修正前。catch は無条件に separationCache.delete(inputPath)。
   OwnerCheck = TRUE : 修正後。自分が登録したエントリのときだけ削除する。 *)
CONSTANTS OwnerCheck, AllowCleanup

VARIABLES pcA,           \* "idle" | "engine" | "killed" | "failed" | "done"
          pcB,           \* "idle" | "engine" | "done"
          trackedA,      \* A の子プロセスが activeProcesses に載っているか
          cache,         \* separationCache の所有者: "none" | "A" | "B"
          cleaned,       \* cleanupAllResources を実行済みか（1回に有界化）
          foreignDelete  \* A の catch が B のエントリを消したか（履歴変数）
vars == <<pcA, pcB, trackedA, cache, cleaned, foreignDelete>>

TypeOK ==
  /\ pcA \in {"idle", "engine", "killed", "failed", "done"}
  /\ pcB \in {"idle", "engine", "done"}
  /\ trackedA \in BOOLEAN
  /\ cache \in {"none", "A", "B"}
  /\ cleaned \in BOOLEAN
  /\ foreignDelete \in BOOLEAN

Init ==
  /\ pcA = "idle" /\ pcB = "idle" /\ trackedA = FALSE
  /\ cache = "none" /\ cleaned = FALSE /\ foreignDelete = FALSE

A_Start ==
  /\ pcA = "idle"
  /\ pcA' = "engine" /\ trackedA' = TRUE
  /\ UNCHANGED <<pcB, cache, cleaned, foreignDelete>>

\* A の分離が成功: 子の終了から separationCache.set まで await は無い
A_Done ==
  /\ pcA = "engine"
  /\ pcA' = "done" /\ trackedA' = FALSE /\ cache' = "A"
  /\ UNCHANGED <<pcB, cleaned, foreignDelete>>

\* ウィンドウ close: kill を送るが close は待たず、追跡表とキャッシュを空にする
Cleanup ==
  /\ AllowCleanup /\ ~cleaned
  /\ cleaned' = TRUE /\ trackedA' = FALSE /\ cache' = "none"
  /\ pcA' = IF pcA = "engine" THEN "killed" ELSE pcA
  /\ UNCHANGED <<pcB, foreignDelete>>

\* B 開始: releaseInputResources。追跡中の A の子は kill して close を待つので、
\* A の catch（削除）は B が先へ進む前に走り終える。追跡外なら待たずに進む
B_Start ==
  /\ pcB = "idle" /\ pcA # "idle"
  /\ pcB' = "engine" /\ cache' = "none"
  /\ IF trackedA /\ pcA = "engine"
       THEN pcA' = "failed" /\ trackedA' = FALSE
       ELSE UNCHANGED <<pcA, trackedA>>
  /\ UNCHANGED <<cleaned, foreignDelete>>

B_Done ==
  /\ pcB = "engine"
  /\ pcB' = "done" /\ cache' = "B"
  /\ UNCHANGED <<pcA, trackedA, cleaned, foreignDelete>>

\* cleanup で kill された A の close が遅れて届き、catch がキャッシュを削除する
A_LateClose ==
  /\ pcA = "killed"
  /\ pcA' = "failed"
  /\ LET deletes == IF OwnerCheck THEN cache = "A" ELSE TRUE
     IN /\ cache' = IF deletes THEN "none" ELSE cache
        /\ foreignDelete' = (foreignDelete \/ (deletes /\ cache = "B"))
  /\ UNCHANGED <<pcB, trackedA, cleaned>>

Next == A_Start \/ A_Done \/ Cleanup \/ B_Start \/ B_Done \/ A_LateClose
Spec == Init /\ [][Next]_vars

\* 失敗した呼び出しは、他の呼び出しが登録したキャッシュを消さない
OwnerOnlyDelete == ~foreignDelete
=============================================================================
