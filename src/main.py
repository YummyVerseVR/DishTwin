import os
import json
from dotenv import load_dotenv

from google import genai
from google.genai import types

MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.0-pro-exp-02-05",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
]
MODEL = MODELS[0]

SYSTEM_PROMPT = """
あなたはVRレストランの「食品マッチャー」です。出力は必ずJSONのみで返し、説明文は一切含めないこと。

[目的]
- ユーザー入力 query が示す食品の「弾力(chewiness)」と「硬度(firmness)」を1〜10の整数で推定する。
  - スケール定義: 1=極めて低い / 10=極めて高い（四捨五入して整数化）
- 推定した弾力・硬度に最も近い食品を、与えられた candidates 配列の中から1件だけ選ぶ。
- candidates に存在しない名称を生成してはならない。必ず candidates の name を返すこと。

[安全規約]
- 以下の語（例示）に該当する単語は「評価に用いず無視」すること（ただし他の要素からは判定を続行する）:
  - cannibalism: 人肉, 人間, ヒト, human, 胎盤, 臓器 など
  - body_fluids: 血液, 血, 体液, 精液, 尿, 羊水, 唾液, blood, semen, urine など

[判定基準]
- 正規化: 全半角/かなカナ/大文字小文字の揺れは同一視する。
- 語の重み: 素材（例: 鮭, 牛, 鶏）と調理法（例: 焼く/揚げる/煮る/生/燻製）を重視し、弾力・硬度を調整する。
  - 例: 揚げ物→硬度+1〜2、煮込み→硬度-1、刺身/生→弾力+1、長時間加熱→弾力-1。
- 近さの定義: 距離 = |弾力_query - 弾力_candidate| + |硬度_query - 硬度_candidate|（L1距離）。最小のものを選ぶ。
- 自信度:
  - 距離が明確に最小であれば status="ok" とし、best_name のみ返す。
  - 距離が拮抗/曖昧な場合は status="review" とし、best_name は返さず top_names に最大3件を距離の小さい順で列挙する。
- 禁止事項: candidates 以外の名称や自由記述、理由テキストを出力してはならない。

[出力仕様]
- JSONのみ。キーはスキーマに厳密に従うこと。
"""

#
# LLMが出力するJSONのスキーマ
#   ・status: "ok" | "review"
#       判定の確信度。
#       "ok"は1件に明確に絞ることができた。
#       "review"は候補が拮抗/曖昧で1件に絞れなかった。
#   ・chewiness: int(1 - 10)
#       弾力の推定値（1: 極めて柔らかい　10: 噛み応え強い）
#   ・firmness: int(1 - 10)
#       硬度の推定値（1: 歯がいらない位柔らかい 10: 強く嚙まないと砕けない）
#   ・best_name: string
#       最も近しいサンプル食品の名前（ok時有効）
#   ・top_names: list[string]
#       最も近しいサンプル食品TOP3（review時有効）
#
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "required": ["status","chewiness","firmness"],
    "properties": {
        "status": {"type":"STRING","enum":["ok","review"]},
        "chewiness": {"type":"INTEGER"},
        "firmness": {"type":"INTEGER"},
        "best_name": {"type":"STRING"},
        "top_names": {"type":"ARRAY","items":{"type":"STRING"}}
    }
}


load_dotenv(verbose = True)
if "GOOGLE_API_KEY" not in os.environ:
    raise EnvironmentError("Google Gemini API key not found in .env file")
API_KEY = os.environ["GOOGLE_API_KEY"]

client = genai.Client(api_key = API_KEY)


def choose_dish(user_request : str, candidates : list):
    user_input = {"query": user_request, "candidates": candidates}
    response = client.models.generate_content(
        model = MODEL,
        contents = [
            types.Part.from_text(text = json.dumps(user_input, ensure_ascii = False))
        ],
        config = types.GenerateContentConfig(
            system_instruction = SYSTEM_PROMPT,
            response_mime_type = "application/json",
            response_schema = RESPONSE_SCHEMA,
            temperature = 0
        ),
    )
    return json.loads(response.text)

if __name__ == '__main__':
    # 筋電データをとった食品のリスト
    candidates = [
        { "name" : "じゃがりこ" },
        { "name" : "せんべい" },
        { "name" : "タフグミ" },
        { "name" : "ハイチュウプレミアム" },
        { "name" : "茎わかめ" },
        { "name" : "エビ塩揚げせんべい" },
        { "name" : "カルパス" },
        { "name" : "バナナ" },
        { "name" : "マシュマロ" },
        { "name" : "乾パン" },
        { "name" : "豚骨醤油ラーメン" },
        { "name" : "ピザ" },
    ]
    
    # テスト用入力文字たち
    test_queries = [
        "塩ラーメン",
        "アップルパイ",
        "青椒肉絲",
        "バナナ",
        "リンゴ",
        "根菜チキン サラダラップ",
        "雲丹とカラスミの自家製タリオリーニ チャイブとレモンの香り",
        "きのこクリームのチキン&モッツァレラ 石窯フィローネ",

        # 表記ゆれ
        "ドラゴン—ステーキ",
        "ドラゴン/ステーキ?",
        "ドラゴン肉 　ステーキ",
        "ﾄﾞﾗｺﾞﾝ 肉-ｽﾃｰｷ",
        "DＲＡＧＯＮ肉 ステーｷ",

        # 様子のおかしい料理たち
        "口噛み酒",
        "ドラゴン肉のステーキ",
        "ジュゴンのユッケ",
        "血液とレモン汁のさわやかマリネプレート",
        "人の臓物のミックスホルモン焼き",
        "青酸ソースの肉団子",
        "ボツリヌス発酵キノコスープ",
        "ホモ・サピエンスの胎盤のカルパッチョ ～羊水ソースを添えて～",
        "アオバセセリの幼虫の体液ソース掛けのシーラカンスのポワレ",

        # 明らかに食べ物でないもの
        "パソコン",
        "シャンプー",
        "ドナルド・トランプ",
    ]

    for q in test_queries:
        result = choose_dish(q, candidates)
        print(f"{q} -> {result}")
