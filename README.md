## 使い方

1. Docker Hubからdockerイメージを取ってきて立ち上げる（起動プロセスはすぐに終了する）
```
docker run -d wakin/nsfw_reporter:latest
```

2. 以下の内容を参考に`config.ini`を作成する
```ini
[settings]
API_BASE_DOMAIN=biwakodon.com
CLIENT_ID=nsfw_reporter
CLIENT_SECRET=********
ACCESS_TOKEN=********
THRESHOLD=0.8
```
- `THRESHOLD`は[Open nsfw model](https://github.com/yahoo/open_nsfw#usage)のスコアからレポートを作成する際の閾値
- アプリに必要な権限は`read`と`write`

3. 停止中のコンテナに`config.ini`をコピーする
```
docker cp config.ini <NAMES>:/workspace/
```

4. コンテナを再起動する
```
docker restart <NAMES>
```

## Open nsfw model
https://github.com/yahoo/open_nsfw
