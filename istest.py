import hashlib
from datetime import datetime, timedelta
from gmssl import sm2, sm4, func
import sqlite3
import uuid
from gmssl import sm3, func


class ShortLinkSystem:

    def __init__(self, db_path='short_links.db'):
        """
        初始化短链接系统，包括数据库连接和SM2密钥对生成
        """
        self.conn = sqlite3.connect(db_path)
        self._init_db()

        # 动态生成SM2密钥对
        self.sm2_private_key, self.sm2_public_key = self._generate_sm2_key_pair()
        self.sm2_crypt = sm2.CryptSM2(private_key=self.sm2_private_key, public_key=self.sm2_public_key)

    def _init_db(self):
        """
        初始化数据库表
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS any_short_chain (
                id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                content TEXT,
                short_code TEXT NOT NULL,
                useful_time DATETIME,
                status INTEGER DEFAULT 1,
                domainKey TEXT NOT NULL,
                publicKey TEXT NOT NULL,
                privateKey TEXT NOT NULL,
                sign TEXT NOT NULL,
                user_times INTEGER,
                oper_user TEXT,
                create_time DATETIME
            )
        ''')
        self.conn.commit()
        print("数据库初始化完成")  # 调试打印

    def _generate_sm2_key_pair(self):
        """
        手动生成 SM2 密钥对
        """
        print("正在生成 SM2 密钥对...")  # 调试打印
        private_key = func.random_hex(64)  # 生成随机私钥
        # 使用 SM2 默认曲线参数手动计算公钥
        ecc_table = sm2.default_ecc_table
        sm2_crypt = sm2.CryptSM2(private_key=private_key, public_key="")
        public_key = sm2_crypt._kg(int(private_key, 16), ecc_table['g'])  # 使用椭圆曲线点乘计算公钥
        print(f"SM2 密钥对生成成功，私钥: {private_key}, 公钥: {public_key}")  # 调试打印
        return private_key, public_key

    def _generate_sm4_key(self):
        """
        生成随机的SM4密钥
        """
        return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:16].encode()

    def _generate_sign(self, params):
        """
        根据输入参数生成签名
        """
        sorted_keys = sorted(params.keys())
        sign_str = ''.join([f'{k}{params[k]}' for k in sorted_keys])
        return hashlib.md5(sign_str.encode()).hexdigest()

    def _sm4_encrypt(self, data, key):
        """
        使用SM4加密数据
        """
        crypt_sm4 = sm4.CryptSM4()
        crypt_sm4.set_key(key, sm4.SM4_ENCRYPT)
        return crypt_sm4.crypt_ecb(data.encode())

    def _sm4_decrypt(self, encrypted_data, key):
        """
        使用SM4解密数据
        """
        crypt_sm4 = sm4.CryptSM4()
        crypt_sm4.set_key(key, sm4.SM4_DECRYPT)
        return crypt_sm4.crypt_ecb(encrypted_data).decode()

    def generate_short_link(self, long_url, valid_hours=24, user=None):
        """
        生成短链接并存储在数据库中
        """
        print("正在生成短链接...")  # 调试打印
        try:
            domain = long_url.split('//')[1].split('/')[0]
        except IndexError:
            domain = long_url.split('/')[0]

        # 生成SM4密钥并加密内容
        domain_key = self._generate_sm4_key()
        encrypted_content = self._sm4_encrypt(long_url, domain_key)

        # 使用SM2公钥加密SM4密钥
        encrypted_key = self.sm2_crypt.encrypt(domain_key)

        # 生成签名
        create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        params = {
            'domain': domain,
            'content': long_url,
            'createTime': create_time,
            'domainKey': domain_key.hex()
        }
        sign = self._generate_sign(params)

        # 存储到数据库
        short_id = str(uuid.uuid4())
        useful_time = (datetime.now() + timedelta(hours=valid_hours)).strftime('%Y-%m-%d %H:%M:%S')

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO any_short_chain 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            short_id,                # id
            domain,                  # domain
            encrypted_content.hex(), # content
            encrypted_key.hex(),     # short_code
            useful_time,             # useful_time
            1,                       # status
            domain_key.hex(),        # domainKey
            self.sm2_public_key,     # publicKey
            self.sm2_private_key,    # privateKey
            sign,                    # sign
            0,                       # user_times
            user,                    # oper_user
            create_time              # create_time
        ))
        self.conn.commit()

        short_link = f"{domain}/{encrypted_key.hex()[:8]}"
        print(f"短链接生成成功: {short_link}")  # 调试打印
        return short_link

    def resolve_short_link(self, short_url):
        """
        解析短链接并返回原始URL
        """
        print("正在解析短链接...")  # 调试打印
        try:
            domain, short_code = short_url.split('/')
        except ValueError:
            raise ValueError("无效的短链接格式")

        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM any_short_chain 
            WHERE domain=? AND short_code LIKE ?
        ''', (domain, f"{short_code}%"))
        record = cursor.fetchone()

        if not record:
            raise ValueError("短链接不存在")

        # 检查是否过期
        useful_time_str = record[4].split('.')[0]
        useful_time = datetime.strptime(useful_time_str, '%Y-%m-%d %H:%M:%S')
        if datetime.now() > useful_time:
            raise ValueError("短链接已过期")

        # 解密SM4密钥
        try:
            encrypted_key = bytes.fromhex(record[3])
            domain_key = self.sm2_crypt.decrypt(encrypted_key)
        except Exception:
            raise ValueError("SM2解密失败")

        # 解密内容
        try:
            encrypted_content = bytes.fromhex(record[2])
            decrypted_content = self._sm4_decrypt(encrypted_content, domain_key)
        except Exception:
            raise ValueError("SM4解密失败")

        # 验证签名
        params = {
            'domain': record[1],
            'content': decrypted_content,
            'createTime': record[12],
            'domainKey': domain_key.hex()
        }
        if self._generate_sign(params) != record[9]:
            raise ValueError("签名验证失败")

        print(f"解析成功: {decrypted_content}")  # 调试打印
        return decrypted_content
class CryptoModule:
    def __init__(self):
        pass

    def sm3_hash(self, message: str) -> str:
        """
        使用SM3算法生成消息摘要
        :param message: 输入的字符串消息
        :return: SM3摘要（十六进制字符串）
        """
        # 转换字符串消息为字节
        message_bytes = message.encode('utf-8')
        # 生成SM3哈希值
        sm3_digest = sm3.sm3_hash(func.bytes_to_list(message_bytes))
        return sm3_digest

if __name__ == "__main__":
    system = ShortLinkSystem()

    # 测试生成和解析
    test_url = "https://www.example.com/path?param1=value1&param2=value2"
    print("开始测试短链接生成和解析...")  # 主程序打印

    # 生成短链接
    short_url = system.generate_short_link(test_url, user="test_user")
    print(f"生成的短链接: {short_url}")  # 打印生成的短链接

    # 查看数据库内容
    cursor = system.conn.cursor()
    cursor.execute('SELECT * FROM any_short_chain')
    rows = cursor.fetchall()
    print("数据库内容:")
    for row in rows:
        print(row)
    if __name__ == "__main__":
        crypto = CryptoModule()
        test_message = "Hello, SM3!"
        print(f"消息: {test_message}")
        print(f"SM3摘要: {crypto.sm3_hash(test_message)}")
    # 解析短链接
    try:
        original = system.resolve_short_link(short_url)
        print(f"解析成功: {original}")  # 打印解析成功的原始 URL
    except Exception as e:
        print(f"解析失败: {str(e)}")  # 打印错误信息