# DishTwin
ユーザーが入力した料理名から 弾力（chewiness）と 硬度（firmness） を 1〜10 の整数で推定し、事前にラベリング済みの候補の食品と照合して 最も近しい1件を決定する。

---
## ユーザー入力（例）
```JSON
{
    "name": "豚骨醤油ラーメン"
}
```

## 出力
LLMから次のような形式のJSONが返ってくる

```JSON
{
    "status": { "type":"string", "enum":["ok","review"] },
    "chewiness": {"type":"integer" },
    "firmness": {"type":"integer"},
    "best_name": {"type":"string"},
    "top_names": {"type":"array","items":{"type":"string"}}
}
```

- status: "ok" | "review":  判定の確信度。
    - "ok": 1件に明確に絞ることができた。
    - "review": 候補が拮抗/曖昧で1件に絞れなかった。
- chewiness: int(1 - 10)
    - 弾力の推定値（1: 極めて柔らかい　10: 噛み応え強い）
- firmness: int(1 - 10)
    - 硬度の推定値（1: 歯がいらない位柔らかい 10: 強く嚙まないと砕けない）
- best_name: string
    - 最も近しいサンプル食品の名前（ok時有効）
- top_names: list[string]
    - 最も近しいサンプル食品TOP3（review時有効）