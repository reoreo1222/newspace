# Newspace クライアント確認サイト

GitHub Pages は `github-pages/` の静的HTMLを `.github/workflows/pages.yml` から公開します。

- 公開URL: `https://reoreo1222.github.io/newspace/`
- 旧サイトのファイルはリポジトリ直下に残しています。
- 更新前の状態は `backup/pre-wordpress-preview-20260924` ブランチにも保存しています。
- 確認サイトは全ページ `noindex` です。
- 問い合わせフォームは確認用で、送信機能を停止しています。

公開前検査:

```sh
python3 scripts/check_github_pages.py
```
