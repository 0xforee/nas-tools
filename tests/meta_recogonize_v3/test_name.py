import re
from app.media.meta import MetaInfo

def remove_tone_marks(text):
    tone_marks = ["ā", "á", "ǎ", "à", "ē", "é", "ě", "è", "ī", "í", "ǐ", "ì", "ō", "ó", "ǒ", "ò", "ū", "ú", "ǔ", "ù",
                  "ü", "ǖ", "ǘ", "ǚ", "ǜ"]
    base_characters = ['a', 'a', 'a', 'a', 'e', 'e', 'e', 'e', 'i', 'i', 'i', 'i', 'o', 'o', 'o', 'o', 'u', 'u', 'u',
                       'u', 'u', 'u', 'u', 'u', 'u']

    for tone_mark, base_char in zip(tone_marks, base_characters):
        text = text.replace(tone_mark, base_char)

    return text
def split_sentence(sentence):
    separators = r'[\(\)\[\]【】]'
    subclauses = re.split(separators, sentence)
    # Filter out empty subclauses
    subclauses = [subclause.strip() for subclause in subclauses if subclause.strip()]
    return subclauses

def parseTv(name: str):
    #  TV 要在 movie 的基础上增加季或者集的匹配
    pass


def paseAnimal(name: str):
    pass

matched_torrent = []

def check_title_valid(origin_name, name):
    """
    检查是有官方名字，并返回匹配的名称
    并依次猜测名字，并返回匹配的名称
    """
    en_name = origin_name['en_name']
    cn_name = origin_name['cn_name']
    pin_name = origin_name['pin_name']
    # 确定 name 中是否包含原始合格的标题
    if name.find(en_name) != -1:
        return en_name, "en"
    else:
        guess_en = guess_and_match_name(en_name, name)
        if guess_en:
            return guess_en, "en"
    if name.find(cn_name) != -1:
        return cn_name, "cn"
    else:
        guess_cn = guess_and_match_name(cn_name, name)
        if guess_cn:
            return guess_cn, "cn"
    if name.find(pin_name) != -1:
        return pin_name, "pin"
    else:
        guess_pin = guess_and_match_name(pin_name, name)
        if guess_pin:
            return guess_pin, "pin"
    return None, None

def guess_and_match_name(language_name, name):
    """

    """
    # 未发现空格，没有分隔符，原始名称之前已经匹配过了，所以这里没有匹配意义了
    if(language_name.find(' ') == -1):
        return None
    split_char = ['.', '-', '_']
    for char in split_char:
        new = language_name.replace(' ', char)
        if name.find(new) != -1:
            return new

    return None


def parseMovie(origin_name, name: str):
    name = remove_tone_marks(name)
    # 移除语调，忽略大小写
    origin_name = {
        'en_name': remove_tone_marks(origin_name['en_name'].lower()),
        'cn_name': origin_name['cn_name'].lower(),
        'pin_name': remove_tone_marks(origin_name['pin_name'].lower()),
    }

    name = name.lower()

    # 1.先根据成对出现的分隔符，比如[],【】，()，来分割子句
    sub_sentences = split_sentence(name)
    if len(sub_sentences) > 0:
        # 多个子句情况 TODO
        # 2. 根据备选项，找出对应的三个并列子句（子句要不同，不能找同一个）（按优先级选择一个），移除在序列子句中的其他标题子句
        pass
    # 大多数情况只有一个子句
    else:
        en_name = origin_name['en_name']
        cn_name = origin_name['cn_name']
        pin_name = origin_name['pin_name']
        # 确定 name 中是否包含原始合格的标题
        valid_name, type = check_title_valid(origin_name, name)
        if valid_name is None:
            # 没有合格名称，匹配失败
            return False
        else:
            # 有合格的标题
            # 3. 如果标题子句只有一个，要排除多个标题的影响。抹除标题子句中其他语种标题（要求连续语种）TODO
            # 4. 如果英文标题不足以有辨识度，某个电影名称可能是其他名称的一部分 TODO
            # 检查标题两侧是否有同语种内容（英语和拼音，中文不用检查）
            if type != 'cn':
                if name.find(valid_name) != -1:
                    if 'A' <= name[name.index(valid_name) + len(valid_name)] <= 'z':
                        return False


        # 如果有合格的标题，再以标题反查一次 tmdb，这样就可以防止标题没有辨识度了。
        # 通过反查回来的列表，来反向过滤一次。

        # 移除标题
        removed_title_name = name.replace(valid_name, "")

        # 识别年份
        meta_info = MetaInfo(title=name)
        print(meta_info.year)
        # 识别集，季

        year = origin_name['year']
        if removed_title_name.find(year) == -1:
            return False

        return True


        # 3. 标题前后的内容是有意义的。所以要以标题为分割符，切分标题子句。（标题子句全匹配就跳过，否则要看看是什么内容）
        # 4. 根据搜索意图，拼接要匹配的年份
        # 4. 处理标题子句的前后内容，处理年份
        # 5.
        # 根据传给网站的英文（或者中文），来向 tmdb 发起同名查询，然后从最后过滤的结果中，滤除不符合要求的电影（这样，整个匹配过程中只需要发起两次网络请求）
        # 快速版，根据年份过滤一次，然后做同名滤除。

    return True




if __name__ == '__main__':
    tv_names = [
        "The Daily Life of the Immortal King S01~S04 1080P~4K WEB-DL AAC H.264",
    "[NC-Raws] 仙王的日常生活 第三季 / The Daily Life of the Immortal King S3 - 06 (CR 1920x1080 AVC AAC MKV)",
    "[GM-Team][国漫][仙王的日常生活 第4季][Xian Wang De Ri Chang Sheng Huo Ⅳ][2023][01-12 Fin][AVC][GB][1080P] ",
        "[TV Series]In the Name of the Brother S01E22 2024 1080p WEB-DL H264 AAC-DramaS@ADWeb[哈尔滨一九四四 第22集 *银河奇异果* ]",
        "侠岚.Shalen.2018.S07.2160p.HQ.WEB-DL.HEVC.10bit.AAC-HDVWEB ",
        ]

    match = {
        'en_name': "Interstellar",
        'cn_name': "星际穿越",
        "pin_name": "Xinjichuanyue",
        'year': '2014'
    }

    cases = [
        "Interstellar 2014 2160p HDR UHD BluRay DTS-HD MA 5.1 2Audio x265 10bit-HDS",
        "Interstellar 2014 2160p UHD Blu-ray HDR10 HEVC DTS-HD MA 5.1",
        "Interstellar 2014 IMAX UHD BluRay 2160p 2Audio DTS-HD MA 5.1 x265 10bit HDR-BeiTai",
        "Interstellar Wars 2016 1080p friDay WEB-DL H.264 AAC-YingWEB",
        "Interstellar 2014 BluRay 2160p x265 10bit 4Audio mUHD-FRDS",
        "Bermuda-interstellar 2022 2160p WEB-DL H.265 AAC-PTerWEB",
        "Interstellar 2014 PROPER 1080p BluRay DTS x264-SoP",
        "Interstellar 2014 IMAX BluRay 1080p x265 10bit AC3 iNT-TLF",
        "Interstellar IMAX 2014 BluRay 1080p x264 DTS 2Audios-CMCT",
        "Interstellar 2014 V2 UHD Bluray 2160p DTS-HD MA 5.1 HDR x265 10bit-CHD",
        "Interstellar 2014 3Disc 2160p UHD Blu-ray HEVC DTS-HD MA 5.1-CMCT",
        "Interstellar 2014 2160p WEB-DL H.265 AAC-AilMWeb",
        "Interstellar 2014 BluRay 1080p x265 10bit 2Audio MNHD-FRDS",
        "Interstellar 2014 BluRay 1080p av1 2Audio-tinyAV",
        "Interstellar 2014 IMAX UHD BluRay 2160p 10bit HDR 2Audio DTS-HD MA 5.1 TrueHD 5 1 x265-beAst",
        "Interstellar 2014 UHD Blu-ray 2016p HEVC DTS-HD MA 5.1-CMCT",
        "Interstellar 2014 1080p WEB-DL H.264 AAC-AGSVWEB",
    ]

    for name in cases:
        if parseMovie(match, name):
            pass
        else:
            print(f"failed {name}")


    print(f"matched: {len(matched_torrent)}")

