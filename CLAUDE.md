# おぼえてタッチ — 開発者向けメモ (CLAUDE.md)

脳卒中・高次脳機能障害のある**大人**向けのワーキングメモリー訓練アプリ。
作業療法士が患者につき添って使うことを想定（評価の代替や医療機器ではない）。
子ども向けではないので、トーンやデザインは常に大人向けを保つこと。

## ファイル構成

```
src/oboete-touch.html   ← 唯一の編集対象（ソースオブトゥルース）
build.py                ← src/ から index.html を生成するビルドスクリプト
package.json             ← esbuildの依存関係（ビルド用、アプリ本体には不要）
index.html               ← GitHub Pages公開用のビルド済みファイル（コミットする）
README.md                ← 利用者向けの説明
```

**編集するのは必ず `src/oboete-touch.html` のみ。** `index.html` は手で直接編集しない
（`build.py` が自動生成するので、次のビルドで上書きされて消える）。

`src/oboete-touch.html` は、タイトルタグから始まり `</script>` で終わる1枚のHTMLフラグメント
（`<html>` `<head>` `<body>` を持たない）。これは意図的な形式で、Claudeのartifact機能
（`https://claude.ai/artifact/WgziotYdTNoniC52Z44SSC`）にそのまま publish できる。
Claude側は最新ブラウザなので変換は不要。GitHub Pages向けだけ `build.py` で変換する。

## ビルド手順

```bash
npm install      # 初回のみ（esbuildをインストール）
python3 build.py # src/oboete-touch.html → index.html を生成
```

生成後、`git add -A && git commit && git push` で GitHub Pages
（`https://just-ot-goodful.github.io/oboete-touch/`）に反映される。
Pages設定は Settings → Pages → Deploy from branch: `main` / `/`（root）。

`build.py` がやっていること：
1. `src/oboete-touch.html` の `<script>` の中身を esbuild で `--target=safari11` に変換
   （古いiPad（iOS 11以降）のSafariは、スクリプト中に未対応の構文が1つでもあると
   スクリプト全体が実行されず「画面は出るがタップしても反応しない」状態になるため）。
2. `<head>`（viewport・PWA用メタタグ等）を追加。
3. 実機で原因不明のエラーが起きた時のために、画面下に赤帯でエラー内容と
   `navigator.userAgent` を表示するガードスクリプトを注入する
   （開発者は実機のコンソールを見られないため、これが唯一の手がかりになる）。

## テスト環境の制約（重要）

この開発はClaude（クラウドのLinuxコンテナ）上で行われており、**実機のiPad・実機のSafari
には一度もアクセスできていない**。動作確認はすべて Playwright + Chromium
（モバイルビューポート・タッチフラグをエミュレート）で行っており、これは
- レイアウト崩れ・はみ出し
- JSの実行エラー
- AudioContext / SpeechSynthesis のAPI呼び出しが実際に発生しているか
を検証できるが、**実際のWebKit（Safari）エンジンの挙動そのもの
（古いiOSの構文制限、オートプレイ制限、発話の既知バグ等）は再現できない。**

したがって、「iPadで動かない」「Safariで音が出ない」等の報告を受けたら、
まず憶測で直すのではなく、既知のSafari/WebKitの制約（下記）から当たりをつけて直し、
可能ならPlaywrightで「エラーが出ていないこと」「該当のAPIが正しく呼ばれていること」
まで確認し、その上で**実機での再確認を必ずユーザーに依頼する**こと。
再現しない場合は、画面下のエラーバナー（上記ガードスクリプト）のスクリーンショットを
送ってもらうよう頼むと手がかりが得られる。

## 直近の修正履歴（2026年10月17日時点）

- iPadで縦スクロールが止まる不具合 → `html,body{overflow-x:hidden}` が原因
  （iOS Safariの既知の癖）。内側の `.wrap{overflow-x:clip}` に変更して解決。
  横向き用の2列CSS Gridレイアウトも追加。
- iPadで画面が全く反応しない不具合 → スクリプト中に `??`（nullish coalescing）等、
  古いSafariが構文解析できない箇所があり、スクリプト全体が死んでいたのが原因と推定。
  esbuild `--target=safari11` 変換 + エラーバナーで対応（上記）。
- Safariで音声（効果音・読み上げ）が再生されない不具合 →
  - Safari/iOSは「ユーザー操作の直後」でなければ音を再生できない制約があるため、
    画面の最初の一回のタップ/クリックで `AudioContext` と `speechSynthesis` を
    明示的にロック解除する処理を追加（`unlockAudio()`、最初のタップで必ず発火）。
  - `SpeechSynthesisUtterance` を変数で参照保持しないとSafariでGCされ、
    発話が途中で消える既知の不具合があるため、グローバル変数で保持するようにした。
  - `speechSynthesis.cancel()` の直後に `speak()` すると声が出ないSafariの
    既知の不具合があるため、少し間を置くようにした。
  - 発話が内部的に約15秒で止まるバグ（Safari/Chrome共通の既知バグ）への対策として、
    定期的に `pause(); resume();` を呼ぶウォッチドッグを追加。
  - バックグラウンドから復帰した際に `AudioContext` を再開する処理を追加。
  - 利用可能な日本語音声を明示的に選んで `utterance.voice` に設定するようにした。
  - **ハードウェアのマナースイッチ（サイレントスイッチ）がオンの場合、iOSはWeb
    Audioの音を強制的に消す仕様であり、これはアプリ側のコードでは解除できない。**
    ユーザーから「音が出ない」と報告があったら、このスイッチの確認も必ず案内すること。

## アプリのアーキテクチャ（ざっくり）

- 単一の `<script>` 内に全ゲームロジックを実装。ビルドツールやフレームワークは使わない。
- 12種類の課題（ゲーム）があり、`ROUND` オブジェクトが課題名（`shop`/`sushi`/`stars`/
  `phone`/`bus`/`med`/`cards`/`train`/`cook`/`locker`/`wallet`/`plan`）→
  `async function roundXxx(my)` へのディスパッチテーブルになっている。
- スパン課題（系列を見せて同じ順/逆順で答える）は `newState` / `step` /
  `spanFeedback` / `roundOut` という共通ヘルパーで実装し、2-up/2-down方式で難易度を
  適応的に上下させる。n-back型課題（寿司・電車）はヒット率/誤反応率で難易度調整する。
- 課題ごとの表示文字列は `UNIT` / `TITLE` / `SHORT` / `TRAIN` / `ICON` / `RULE` /
  `LVTXT` という連想配列にまとめてあり、新しいゲームを足すときはここに
  `Object.assign` で追記するパターンになっている。
- 効果音はWeb Audio APIのオシレーター（`osc()`/`SFX`オブジェクト）のみで、
  音声ファイルは一切使っていない。読み上げは `speechSynthesis`（日本語TTS）。
- 利用者ごとの設定・レベル・履歴は `localStorage` に `ot3.xxx.<userId>` の形で
  名前空間を分けて保存している（複数患者の切り替えに対応）。

## デザイン上の方針（変更時に守ること）

- 対象は**成人**（子ども向けの絵柄・言い回しにしない）。
- 効果音・読み上げ・BGMはオン/オフ可能。難易度は患者ごとに引き継がれる。
- 1課題あたり短時間（1ラウンド〜数分）で遊べる「お出かけ」的な体験を重視している
  （退屈させない、生活場面に紐づけた内容にする）。
- 根拠（文献）に基づいた難易度調整であること。README末尾の文献リストを参照。
