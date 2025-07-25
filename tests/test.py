import base64

import utils.InteractWordV2 as interact_word_v2_pb2

encoded_data = "CMCxxs0EEhLljYPljYPlrrbjga7nqbrkuIMiAwYDASgBMLS5ieEGOJryssMGQI6VifC4NEouCMXl1wwQGBoJ5aW96L+Q5Y2DIMuoaSjLqGkwkrvKAjjLqGlAAWCR10loiaDsF2IAeLrnpJXhzoyoGIABA5oBALIB+QEIwLHGzQQSaQoS5Y2D5Y2D5a6244Gu56m65LiDEkpodHRwczovL2kwLmhkc2xiLmNvbS9iZnMvZmFjZS9mNjBmOTNjYjhiNGNkZmRjYjhjY2FiMzlmYWQ4NDZhNTQxZWNmOGNkLmpwZ0IHIzAwRDFGMRppCgnlpb3ov5DljYMQGBjLqGkgkrvKAijLqGkwy6hpOPXqEkgBUMXl1wxgiaDsF3oJIzQzQjNFM0NDggEJIzQzQjNFM0NDigEJIzVGQzdGNEZGkgEJI0ZGRkZGRkZGmgEJIzAwMzA4Qzk5IgIIHDIXCAMSEzIwMjUtMDctMjMgMjM6NTk6NTm6AQA="

# 4. Base64转字节流
binary_data = base64.b64decode(encoded_data)

# 5. 反序列化
interact_word = interact_word_v2_pb2.INTERACT_WORD_V2().ParseFromString(binary_data)
interact_word.ParseFromString(binary_data)
print(f"用户ID: {interact_word.uid}")
print(f"用户名: {interact_word.uname}")
print(interact_word.msg_type)
