# おぼえてタッチ — 開発者向けメモ (CLAUDE.md)

脳卒中・高次脳機能障害のある**大人**向けのワーキングメモリー訓練アプリ。
作業療法士が患者につき添って使うことを想定（評価の代替や医療機器ではない）。
子ども向けではないので、トーンやデザインは常に大人向けを保つこと。

## ファイル構成

```
src/oboete-touch.html   ← 唯一の編集対象（ソースオブトゥルース）
build.py                ← src/ から index.html を生成するビルドスクリプト
package.json             ← esbuildの依存関係（ビルド用、アプリ本体には不要）
tools/oldsafari.py       ← 古いSafari（iOS 12）の擬似テスト（下記）
tools/montage.py         ← 擬似テストのスクリーンショットを横に並べる
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
2. `<style>` の中身にも古いSafari向けの代替指定を自動で足してから esbuild で変換する：
   - `clamp(a,b,c)` の前に `max(a,min(b,c))`（iOS 12/13用）と単純な値（iOS 11.2以前用）を挿入
   - `min()` の前に単純な値（%/vwの方）を挿入
   - `gap` の前に `grid-gap`（iOS 11のgrid用）を挿入
   - esbuildが `inset` → top/right/bottom/left に展開し、`-webkit-` 接頭辞を付ける
3. **flexboxの `gap` の代替（polyfill）** を注入する。iOS 14.5未満はflexの `gap` を無視し、
   ボタンや部品がくっついて画面が崩れる（これが古いiPadでの崩れの最大の原因だった）。
   - headのスクリプトで flex gap が効くか判定し、効かなければ `<html class="nfg">` にする
   - body末尾のスクリプトが、ビルド時にCSSから抜き出した「どのセレクタにどのgapか」の表を使い、
     子要素に margin を付けて同じ間隔を作る（画面が変わるたびに MutationObserver で付け直す）
   - 新しいブラウザでは `nfg` にならないので何もしない
   - **CSSで新しく flex の `gap` を書いても、build.py が自動で表に入れるので追加作業は不要。**
4. `<head>`（viewport・PWA用メタタグ等）を追加。
5. 実機で原因不明のエラーが起きた時のために、画面下に赤帯でエラー内容と
   `navigator.userAgent` を表示するガードスクリプトを注入する
   （開発者は実機のコンソールを見られないため、これが唯一の手がかりになる）。
6. iOS 10以前の端末では、エラーの代わりに「iOS 11以降で動きます」という案内を全画面で出す。

## 対応範囲（古いSafari）

- **対応：iOS 11以降**（例：iPad Air 1・iPad mini 2/3 は iOS 12 まで、iPad 第5世代以降）。
- **非対応：iOS 10以前**（iPad 第4世代以前）。esbuildが Safari 10 向けの `const`/`let`
  変換に対応していないため（Safari 10の `let`/`const` には不具合がある）。
  対応させるならBabel等で ES5 まで落とす必要があるが、2012年以前の端末なので見送った。
- `src/` に新しいCSS・JS機能を書くときは、iOS 11〜14で使えるかを確認すること。
  特に以下は自動では補えないので、使うなら `@supports` などで代替を書く：
  `aspect-ratio`（iOS 15）、`overflow:clip`（iOS 16）、論理プロパティ `padding-inline` 等
  （iOS 14.1）、`:is()`/`:where()`/`:has()`、`color-mix()`、`dvh`、CSSネスト、
  JSの `Array.prototype.at`/`flat`、`String.prototype.replaceAll`、`structuredClone` 等。
  （esbuildは構文は変換するが、実行時の関数やCSS機能の代わりは用意しない）

## 古いSafariの擬似テスト（tools/oldsafari.py）

実機がないため、Chromiumで「iOS 12が読めないCSS・JS機能を取り除いた状態」を再現して確認する。
3つのモードで全画面・全12ゲームを撮影し、数値（はみ出し・高さ・JSエラー）を比較する：
- `modern`：普通のChromium
- `old`：flex gap を無効化＋polyfill強制ON、`clamp()`/`aspect-ratio`/`overflow:clip` を削除、
  iOS 12にないJS関数を削除（＝修正後の古いiPadの見た目）
- `broken`：`old` と同じだがpolyfillなし（＝修正前の古いiPadの見た目。テストが効いている確認用）

```bash
pip install playwright pillow --break-system-packages   # 初回のみ
python3 tools/oldsafari.py "$PWD/index.html" /tmp/os            # 全部（15分ほど）
VP=phone ONLY=cards python3 tools/oldsafari.py "$PWD/index.html" /tmp/os   # 一部だけ
python3 tools/montage.py /tmp/os ipad_p home,cards /tmp/mt        # 3モードを横に並べた画像
```
`modern` と `old` の見た目が一致していればOK。これでも実際のWebKitではないので、
最後は実機での確認をユーザーに依頼すること。

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

- 古いSafariで画面が崩れる不具合（2026年10月18日）→
  - flexboxの `gap` 非対応（iOS 14.5未満）が主因。build.py で polyfill を注入（上記）。
  - 星空の `aspect-ratio` 代替が `padding-bottom:75%`（親の幅基準）で縦に伸びすぎていた
    → `.sky::before{padding-top:75%}`（自身の幅基準）に修正。
  - 神経衰弱のカードが小さく潰れていた → 代替指定で `.scene.cards{justify-content:stretch}`
    と `.card{padding:0}`（ボタン標準の内側余白で縦横比がずれる）を追加。
  - 論理プロパティ（`padding-inline` 等）を通常の上下左右指定に書き換え。
  - `.wrap` に `overflow-x:hidden` を `clip` の前に追加（iOS 15以前用）。
  - ボタン・入力欄に `-webkit-appearance:none`（古いiOSの標準の見た目を消す）。

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
