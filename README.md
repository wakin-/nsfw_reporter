## 使い方

1. 以下の内容を参考に環境変数ファイルを用意する
```ini:envfile
API_DOMAIN=biwakodon.com
CLIENT_ID=nsfw_reporter
CLIENT_SECRET=********
ACCESS_TOKEN=********
THRESHOLD=0.8
```
- `THRESHOLD`は[Open nsfw model](https://github.com/yahoo/open_nsfw#usage)のスコアからレポートを作成する際の閾値
- アプリに必要な権限は`read`と`write`

2. Docker Hubからdockerイメージを取ってきて、環境変数ファイルを指定して立ち上げる
```
docker run -d --env-file envfile wakin/nsfw_reporter
```

## Open nsfw model
https://github.com/yahoo/open_nsfw
