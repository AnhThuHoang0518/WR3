#!/usr/bin/env python3
"""Generate a self-contained VSF Finding-board HTML deck from approved WR3 MI Markdown."""

from __future__ import annotations

import argparse
import base64
import html
import json
import re
import sys
import unicodedata
from collections import OrderedDict
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


REQUIRED_GATES = (
    ("json", "reviews/01-news-relevance-decision.json", "overall_status", "APPROVED"),
    ("json", "reviews/02-opportunity-threat-decision.json", "overall_status", "APPROVED"),
    ("md", "reviews/product-mapping-review.md", "status", "REVIEWED_ACCEPTED"),
    ("md", "reviews/product-gap-review.md", "status", "REVIEWED_ACCEPTED"),
    ("json", "reviews/03-product-action-decision.json", "overall_status", "APPROVED"),
)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
HEADING_FONT_PATH = ASSETS_DIR / "fonts" / "VSFPro.ttf"
BODY_FONT_PATH = ASSETS_DIR / "fonts" / "Lexend-VariableFont_wght.ttf"
COVER_ART_PATH = ASSETS_DIR / "cover-network-diagram.png"
COVER_BACKGROUND_PATH = ASSETS_DIR / "backgrounds1.png"


@dataclass
class MarkdownBlock:
    heading: str
    lines: list[str] = field(default_factory=list)


@dataclass
class MarkdownSection:
    heading: str
    lines: list[str] = field(default_factory=list)
    blocks: list[MarkdownBlock] = field(default_factory=list)


@dataclass
class Report:
    title: str
    run_id: str
    report_time: str
    crawl_window: str
    sections: "OrderedDict[str, MarkdownSection]"


@dataclass
class Slide:
    markup: str
    section: str
    title: str
    classes: str = ""


@dataclass
class PresentationOverlay:
    source_path: Path
    cover_title: str
    cover_subtitle: str
    cover_date: str
    news: dict[str, dict[str, object]]


def norm(value: str) -> str:
    value = unicodedata.normalize("NFD", value.lower())
    return "".join(ch for ch in value if unicodedata.category(ch) != "Mn")


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def keep_phrase_groups(value: object) -> str:
    """Escape copy while keeping editorial phrases together on desktop layouts."""
    rendered = esc(value)
    for phrase in (
        "hành trình khách hàng",
        "AI lấy con người làm trung tâm",
        "Product Mapping",
        "Product Gap",
    ):
        escaped_phrase = esc(phrase)
        rendered = rendered.replace(escaped_phrase, f'<span class="mi-keep">{escaped_phrase}</span>')
    return rendered


def presentation_cover_date(value: object) -> str:
    """Render the reporting week and its inclusive date range for the cover."""
    text = str(value).strip()
    dates = re.findall(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if len(dates) >= 2:
        end_day, end_month, _ = (int(part) for part in dates[-1])
        week_number = (end_day - 1) // 7 + 1
        start = "/".join(part.zfill(2) for part in dates[0][:2]) + f"/{dates[0][2]}"
        end = "/".join(part.zfill(2) for part in dates[-1][:2]) + f"/{dates[-1][2]}"
        return f"Tuần {week_number} - Tháng {end_month} ({start} – {end})"
    return text


def clean_inline(value: str) -> str:
    value = value.strip()
    value = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", value)
    value = value.replace("**", "").replace("__", "").replace("`", "")
    return re.sub(r"\s+", " ", value).strip()


def clean_atom(value: str) -> str:
    return re.sub(r"[.;]+$", "", value.strip())


def capitalize_initial(value: str) -> str:
    """Capitalize the first visible character for sentence-style list items."""
    return value[:1].upper() + value[1:] if value else value


def normalize_customer_copy(value: object) -> str:
    """Apply the approved khách -> khách hàng wording normalization to displayed copy."""
    return re.sub(
        r"\bkhách\b(?!\s+hàng)",
        lambda match: "Khách hàng" if match.group(0)[:1].isupper() else "khách hàng",
        str(value),
        flags=re.IGNORECASE,
    )


FINDING_BOARD_COPY_REPLACEMENTS = {
    "đa chức năng":
        "tích hợp đa dịch vụ",
    "AI tại địa điểm đông người đang chuyển sang vận hành có kiểm soát, ưu tiên trải nghiệm liền mạch và hạn chế gián đoạn cho khách hàng":
        "AI tại địa điểm đông người đang chuyển sang vận hành có kiểm soát, ưu tiên trải nghiệm liền mạch cho khách hàng",
    "Smart City dịch chuyển từ các dự án đơn lẻ sang hệ sinh thái tích hợp và chuẩn hóa, giúp cư dân tiếp cận dịch vụ đô thị liền mạch và thuận tiện hơn":
        "Smart City dịch chuyển từ các dự án đơn lẻ sang hệ sinh thái tích hợp và chuẩn hóa, giúp cư dân tiếp cận dịch vụ đô thị dễ dàng hơn",
    "Khảo sát một sân vận động và một khu vui chơi để tìm ba điểm khách hoặc nhân viên gặp khó khăn nhiều nhất. Sau đó kiểm tra xem các bộ phận có cần một cách chung để chia sẻ thông tin và phối hợp hỗ trợ khách trong toàn bộ hành trình hay không.":
        "Khảo sát thực tế sân vận động và khu vui chơi để tìm các điểm nghẽn khi sử dụng dịch vụ. Từ đó đánh giá nhu cầu về kênh chia sẻ thông tin chung giúp các bộ phận phối hợp hỗ trợ khách hàng xuyên suốt hành trình.",
    "AI tại các địa điểm đông người đang chuyển từ giám sát tự động đơn thuần sang một cách tiếp cận toàn diện hơn, kết hợp công nghệ với hạ tầng, đào tạo nhân sự, cơ chế quản trị và quy trình ứng phó an ninh. Mục tiêu là nâng cao an toàn nhưng vẫn duy trì trải nghiệm thuận tiện, thoải mái cho khách.":
        "Ứng dụng AI tại các địa điểm đông người đang được chuyển từ giám sát tự động đơn thuần sang một cách tiếp cận toàn diện hơn, kết hợp công nghệ với hạ tầng, đào tạo nhân sự, cơ chế quản trị và quy trình ứng phó an ninh. Mục tiêu là nâng cao an toàn nhưng vẫn duy trì trải nghiệm thuận tiện, thoải mái cho khách hàng.",
    "Chuẩn bị một thử nghiệm có kiểm soát cho AI an ninh tại Sân vận động thông minh. Thử nghiệm phải đo cảnh báo sai, thời gian phản ứng và ảnh hưởng đến luồng vào cửa; đồng thời bảo đảm con người kiểm tra quyết định của AI và dữ liệu cá nhân được bảo vệ.":
        "Chuẩn bị thử nghiệm có kiểm soát cho giải pháp AI an ninh tại Sân vận động thông minh, với các chỉ số đo lường rõ ràng: tỷ lệ cảnh báo sai, thời gian phản ứng và tác động đến luồng khách hàng vào cửa. Đồng thời bảo đảm mọi quyết định của AI đều có con người rà soát và dữ liệu cá nhân được bảo vệ đúng quy định.",
    "Các dự án Smart City đang chuyển từ các hệ thống IoT rời rạc sang mô hình kết nối và chia sẻ dữ liệu trên nền tảng chung, với tiêu chuẩn thống nhất và sự phối hợp giữa nhiều đối tác. Đồng thời, giải pháp cần được thử nghiệm trong môi trường thực tế và chứng minh giá trị cụ thể đối với người dân trước khi triển khai rộng.":
        "Các dự án Smart City đang chuyển từ các hệ thống IoT rời rạc sang mô hình kết nối và chia sẻ dữ liệu trên nền tảng chung, với tiêu chuẩn thống nhất và sự phối hợp giữa nhiều đối tác. Đồng thời, giải pháp cần được thử nghiệm trong môi trường thực tế và chứng minh giá trị cụ thể đối với người dân trước khi mở rộng triển khai.",
    "Xây dựng một kiến trúc mẫu và thử nghiệm kết nối ba luồng dữ liệu IoT đô thị (ví dụ: giao thông, an ninh và môi trường), nhằm đánh giá khả năng liên thông giữa các hệ thống, chất lượng dữ liệu và hiệu quả phối hợp giữa các đơn vị khi xử lý tình huống thực tế.":
        "Xây dựng kiến trúc mẫu và thử nghiệm kết nối các luồng dữ liệu IoT đô thị nhằm đánh giá khả năng liên thông giữa các hệ thống, chất lượng dữ liệu và hiệu quả phối hợp giữa các đơn vị khi xử lý tình huống thực tế.",
    "Trước đây, sân vận động và khu vui chơi chủ yếu tập trung phục vụ khách trong thời gian sự kiện. Hiện nay, khách được hỗ trợ từ lúc chuẩn bị đến, vào cổng, tham gia sự kiện, xử lý tình huống phát sinh cho đến các hoạt động ngoài ngày sự kiện.":
        "Trước đây, sân vận động và khu vui chơi chủ yếu tập trung phục vụ khách hàng trong thời gian sự kiện. Hiện nay, khách hàng được hỗ trợ từ lúc chuẩn bị đến, vào cổng, tham gia sự kiện, xử lý tình huống phát sinh cho đến các hoạt động ngoài ngày sự kiện.",
    "Nền tảng điều phối hành trình khách tại địa điểm trải nghiệm":
        "Nền tảng điều phối hành trình khách hàng tại địa điểm trải nghiệm",
    "Catalog hiện chưa ghi nhận sản phẩm Core VSF nào có thể điều phối toàn bộ hành trình của khách tại sân vận động hoặc khu vui chơi.":
        "Catalog hiện chưa ghi nhận sản phẩm Core VSF nào có thể điều phối toàn bộ hành trình của khách hàng tại sân vận động hoặc khu vui chơi.",
    "Chuyển đầy đủ yêu cầu hỗ trợ cho bộ phận tiếp theo để khách không phải trình bày lại":
        "Chuyển tiếp đầy đủ thông tin hỗ trợ cho bộ phận tiếp theo để khách hàng không phải lặp lại yêu cầu",
    "Khảo sát một sân vận động và một khu vui chơi. Vẽ lại toàn bộ hành trình của khách và tìm ba chỗ gây chờ đợi, nhầm lẫn hoặc gián đoạn nhiều nhất.":
        "Khảo sát sân vận động và khu vui chơi để tìm các điểm gây gián đoạn hành trình của khách hàng.",
    "Hoàn thành hai service blueprint mô tả hành trình khách, lập bảng chỉ số hiện trạng và tổng hợp báo cáo go/no-go cho một pilot giới hạn trong ba quy trình đã được xác minh.":
        "Hoàn thành sơ đồ mô tả hành trình và cách thức phục vụ khách hàng, xây dựng bảng chỉ số hiện trạng và tổng hợp báo cáo đánh giá có nên triển khai thử nghiệm hay không trong phạm vi quy trình đã được xác minh.",
    "Có bộ yêu cầu đã được kiểm chứng, phạm vi thử nghiệm rõ ràng, KPI cần đo và quyết định có nên đầu tư tiếp hay không.":
        "Có kết quả khảo sát đã được kiểm chứng, phạm vi thử nghiệm rõ ràng, KPI cần đo và quyết định có nên đầu tư tiếp hay không.",
    "AI tại địa điểm đông người không còn chỉ là camera hoặc công cụ tự động phát cảnh báo. AI đang trở thành một phần của quy trình vận hành, trong đó nhân viên được đào tạo, con người kiểm tra quyết định và các quy tắc về an toàn, quyền riêng tư được xác định rõ.":
        "Ứng dụng AI tại các địa điểm đông người không còn dừng ở camera giám sát hay cảnh báo tự động. AI đang trở thành một mắt xích trong quy trình vận hành, nơi nhân viên được đào tạo bài bản, quyết định của AI có con người rà soát, và các quy tắc về an toàn, quyền riêng tư được quy định rõ ràng.",
    "AI an ninh có thể làm khách phải kiểm tra không cần thiết, chậm vào cửa hoặc lo ngại về quyền riêng tư nếu hệ thống thiếu minh bạch, thường xuyên cảnh báo sai hoặc không có quy trình giải thích quyết định.":
        "Hệ thống AI an ninh cảnh báo sai hoặc thiếu minh bạch trong quyết định có thể dẫn đến kiểm tra không cần thiết, làm chậm quá trình ra vào và gây lo ngại về quyền riêng tư cho khách hàng.",
    "Địa điểm đông người muốn dùng AI để phát hiện rủi ro, nhưng chưa có cách thống nhất để con người kiểm tra quyết định, đo cảnh báo sai và bảo vệ quyền riêng tư mà không làm chậm luồng khách.":
        "Các địa điểm đông người muốn ứng dụng AI để phát hiện rủi ro, nhưng vẫn thiếu quy trình thống nhất để con người kiểm tra kết quả, theo dõi cảnh báo sai và bảo vệ quyền riêng tư, đồng thời bảo đảm trải nghiệm của khách hàng không bị gián đoạn.",
    "Chuẩn bị một thử nghiệm AI an ninh tại Smart Stadium. AI sẽ gợi ý cảnh báo, nhưng nhân viên phải kiểm tra và quyết định trước khi can thiệp. Thử nghiệm cần đo cảnh báo sai, thời gian phản ứng, quyền riêng tư và ảnh hưởng đến tốc độ khách đi qua cổng.":
        "Chuẩn bị thử nghiệm giải pháp AI an ninh tại Sân vận động theo mô hình AI đề xuất cảnh báo, con người quyết định. Thử nghiệm cần đo tỷ lệ cảnh báo sai, thời gian phản ứng và tốc độ khách hàng qua cổng, đồng thời bảo đảm tuân thủ các yêu cầu về quyền riêng tư.",
    "Có đề cương thử nghiệm nêu rõ phạm vi, cách con người kiểm soát AI, KPI an toàn–trải nghiệm và điều kiện để quyết định tiếp tục hay dừng.":
        "Có kế hoạch thử nghiệm rõ ràng về phạm vi, cách con người giám sát AI, các chỉ số về an toàn và trải nghiệm khách hàng, cùng tiêu chí để quyết định tiếp tục hay dừng thử nghiệm.",
    "Chọn một luồng vào cửa để thử nghiệm, xây dựng quy trình pilot và diễn tập tình huống với đội an ninh nhằm thống nhất chỉ số đánh giá, giới hạn can thiệp và điều kiện dừng.":
        "Chọn luồng vào cửa để thử nghiệm, xây dựng quy trình thử nghiệm và diễn tập tình huống với đội an ninh nhằm thống nhất chỉ số đánh giá, giới hạn can thiệp và điều kiện dừng.",
    "Trước đây, mỗi hệ thống Smart City thường được triển khai riêng. Hiện nay, khả năng cạnh tranh phụ thuộc nhiều hơn vào việc kết nối nhiều loại thiết bị và dữ liệu, tuân theo tiêu chuẩn chung, phối hợp đối tác và thử nghiệm trong môi trường thật.":
        "Trước đây, các hệ thống Smart City thường được triển khai độc lập. Hiện nay, khả năng cạnh tranh phụ thuộc nhiều hơn vào khả năng kết nối nhiều loại thiết bị và dữ liệu đa nguồn, tuân theo tiêu chuẩn chung, phối hợp đối tác và thử nghiệm trong môi trường thực tế.",
    "Nhà cung cấp có nguy cơ không được chọn cho các chương trình Smart City lớn nếu sản phẩm không kết nối được với hệ thống khác, không hỗ trợ tiêu chuẩn cần thiết hoặc thiếu đối tác triển khai.":
        "Sản phẩm không kết nối được vào nền tảng dữ liệu chung của đô thị, chưa đáp ứng tiêu chuẩn bắt buộc hoặc thiếu đối tác triển khai sẽ khiến nhà cung cấp mất cơ hội tham gia các chương trình Smart City quy mô lớn.",
    "Thành phố phải kết nối nhiều thiết bị, nguồn dữ liệu và hệ thống do các nhà cung cấp khác nhau phát triển. Nếu mỗi hệ thống dùng giao diện và cách tổ chức dữ liệu riêng, việc tích hợp sẽ tốn kém, dễ phụ thuộc một nhà cung cấp và khó biến dữ liệu thành hành động phục vụ người dân.":
        "Thành phố cần kết nối nhiều thiết bị, nguồn dữ liệu và hệ thống từ các nhà cung cấp khác nhau. Nếu mỗi hệ thống sử dụng cách kết nối và tổ chức dữ liệu riêng, việc tích hợp sẽ tốn nhiều chi phí, khó mở rộng và dễ phụ thuộc vào một nhà cung cấp, đồng thời khiến dữ liệu khó được khai thác để cải thiện dịch vụ và trải nghiệm của người dân.",
    "Kết nối thiết bị IoT và hệ thống đô thị của nhiều nhà cung cấp rồi đưa dữ liệu về một nơi để cùng khai thác":
        "Kết nối thiết bị IoT và các hệ thống đô thị từ nhiều nhà cung cấp, đưa dữ liệu về một nơi để dễ dàng chia sẻ và khai thác",
    "Chuyển dữ liệu từ nhiều định dạng sang mô hình chung và kiểm tra các hệ thống có trao đổi đúng dữ liệu, trạng thái và lệnh xử lý hay không":
        "Chuẩn hóa dữ liệu từ nhiều hệ thống về một cấu trúc chung và kiểm tra khả năng trao đổi dữ liệu, trạng thái và lệnh xử lý giữa các hệ thống",
    "Theo dõi thiết bị, độ đầy đủ và độ kịp thời của dữ liệu, đồng thời chỉ rõ nguồn gây lỗi":
        "Theo dõi tình trạng thiết bị, độ đầy đủ và kịp thời của dữ liệu, từ đó xác định rõ hệ thống hoặc nguồn phát sinh lỗi",
    "Chuyển cảnh báo đến đúng đơn vị chuyên ngành, theo dõi phản hồi và cập nhật trạng thái xử lý giữa các bên":
        "Chuyển cảnh báo đến đúng đơn vị chuyên ngành, từ đó theo dõi phản hồi và cập nhật trạng thái xử lý giữa các bên liên quan",
    "Liên kết dữ liệu vận hành với chỉ số dịch vụ để cho biết việc xử lý đã cải thiện di chuyển, an toàn hoặc môi trường như thế nào":
        "Kết nối dữ liệu vận hành với các chỉ số dịch vụ để đo lường mức độ cải thiện thực tế về di chuyển, an toàn và môi trường",
    "Chuẩn bị một kiến trúc mẫu và thử kết nối ba luồng dữ liệu IoT đô thị. Thử nghiệm phải kiểm tra khả năng trao đổi dữ liệu, chất lượng dữ liệu và cách các đơn vị phối hợp phản ứng khi có cảnh báo.":
        "Chuẩn bị kiến trúc mẫu và thử kết nối các luồng dữ liệu IoT đô thị. Thử nghiệm phải kiểm tra khả năng trao đổi dữ liệu, chất lượng dữ liệu và cách các đơn vị phối hợp phản ứng khi có cảnh báo.",
    "Hoàn thành kiến trúc tham chiếu, ma trận xác định phần cần tự xây dựng hoặc hợp tác, ba kết nối mẫu và kế hoạch pilot có tiêu chí nghiệm thu rõ ràng.":
        "Hoàn thiện kiến trúc tổng thể và xác định rõ phần nào cần tự phát triển, phần nào cần hợp tác với đối tác. Đồng thời, xây dựng kế hoạch thử nghiệm với tiêu chí đánh giá rõ ràng.",
}


EXECUTIVE_SUMMARY_EDITORIAL = {
    ("SIGNAL-001", "ACTION-001"): {
        "signal": "Trải nghiệm tại sân vận động và khu vui chơi không còn giới hạn trong thời gian diễn ra sự kiện, mà được mở rộng thành hành trình xuyên suốt trước – trong – sau sự kiện và qua các hoạt động cộng đồng quanh năm.",
        "signal_bold": (
            "không còn giới hạn trong thời gian diễn ra sự kiện",
            "mở rộng thành hành trình xuyên suốt",
        ),
        "action": "Khảo sát thực tế sân vận động và khu vui chơi để tìm các điểm nghẽn khi sử dụng dịch vụ. Từ đó đánh giá nhu cầu về kênh chia sẻ thông tin chung giúp các bộ phận phối hợp hỗ trợ khách hàng xuyên suốt hành trình.",
        "action_bold": (
            "tìm các điểm nghẽn khi sử dụng dịch vụ.",
            "nhu cầu về kênh chia sẻ thông tin chung",
        ),
    },
    ("SIGNAL-002", "ACTION-002"): {
        "signal": "AI tại các địa điểm đông người đang chuyển từ giám sát tự động đơn lẻ sang mô hình vận hành có kiểm soát và toàn diện hơn, kết hợp công nghệ, hạ tầng, đào tạo nhân sự, quản trị và quy trình ứng phó. Cách tiếp cận này giúp nâng cao an toàn nhưng vẫn bảo đảm trải nghiệm khách hàng liền mạch, thuận tiện và ít bị gián đoạn.",
        "signal_bold": (
            "AI tại các địa điểm đông người đang chuyển từ giám sát tự động đơn lẻ sang mô hình vận hành có kiểm soát và toàn diện hơn",
            "nâng cao an toàn",
            "trải nghiệm khách hàng liền mạch, thuận tiện và ít bị gián đoạn",
        ),
        "action": "Chuẩn bị thử nghiệm có kiểm soát cho giải pháp AI an ninh tại Sân vận động thông minh, với các chỉ số đo lường rõ ràng: tỷ lệ cảnh báo sai, thời gian phản ứng và tác động đến luồng khách hàng vào cửa. Đồng thời bảo đảm mọi quyết định của AI đều có con người rà soát và dữ liệu cá nhân được bảo vệ đúng quy định.",
        "action_bold": (
            "thử nghiệm có kiểm soát",
            "giải pháp AI an ninh tại Sân vận động thông minh",
            "bảo đảm mọi quyết định của AI đều có con người rà soát",
            "dữ liệu cá nhân được bảo vệ đúng quy định.",
        ),
    },
    ("SIGNAL-003", "ACTION-003"): {
        "signal": "Các dự án Smart City đang chuyển từ các hệ thống IoT rời rạc sang mô hình kết nối và chia sẻ dữ liệu trên nền tảng chung, với tiêu chuẩn thống nhất và sự phối hợp giữa nhiều đối tác. Đồng thời, giải pháp cần được thử nghiệm trong môi trường thực tế và chứng minh giá trị cụ thể đối với người dân trước khi mở rộng triển khai.",
        "signal_bold": (
            "dự án Smart City",
            "chuyển từ các hệ thống IoT rời rạc",
            "sang mô hình kết nối và chia sẻ dữ liệu",
            "tiêu chuẩn thống nhất",
        ),
        "action": "Xây dựng kiến trúc mẫu và thử nghiệm kết nối các luồng dữ liệu IoT đô thị nhằm đánh giá khả năng liên thông giữa các hệ thống, chất lượng dữ liệu và hiệu quả phối hợp giữa các đơn vị khi xử lý tình huống thực tế.",
        "action_bold": (
            "Xây dựng kiến trúc mẫu",
            "nhằm đánh giá khả năng liên thông giữa các hệ thống, chất lượng dữ liệu và hiệu quả phối hợp giữa các đơn vị khi xử lý tình huống thực tế.",
        ),
    },
}


def finding_board_copy(value: object) -> str:
    """Apply user-approved presentation-only Vietnamese copy refinements."""
    text = str(value)
    for source, replacement in FINDING_BOARD_COPY_REPLACEMENTS.items():
        text = re.sub(re.escape(source), lambda _: replacement, text, flags=re.IGNORECASE)
    return normalize_customer_copy(text)


def finding_connection_copy(value: object) -> str:
    """Keep the approved connection meaning while removing a redundant lead-in."""
    text = finding_board_copy(value)
    return re.sub(r"^(?:Điều này\s+)?Cho thấy\s+", "", text, flags=re.IGNORECASE).strip()


def render_exact_bold_phrases(text: str, phrases: Iterable[str], label: str) -> str:
    """Render exact, non-overlapping Word emphasis without changing the copy."""
    matches: list[tuple[int, int]] = []
    for phrase in phrases:
        if text.count(phrase) != 1:
            raise ValueError(f"{label} bold phrase must occur exactly once: {phrase}")
        start = text.find(phrase)
        matches.append((start, start + len(phrase)))
    matches.sort()
    for previous, current in zip(matches, matches[1:]):
        if current[0] < previous[1]:
            raise ValueError(f"{label} bold phrases must not overlap")
    parts: list[str] = []
    cursor = 0
    for start, end in matches:
        parts.append(esc(text[cursor:start]))
        parts.append(f'<strong class="mi-exec-emphasis">{esc(text[start:end])}</strong>')
        cursor = end
    parts.append(esc(text[cursor:]))
    return "".join(parts)


def extract_ids(value: str, prefix: str) -> list[str]:
    """Return ordered lineage IDs already present in the approved Markdown."""
    return list(dict.fromkeys(re.findall(rf"\b{re.escape(prefix)}-[A-Z0-9-]+\b", value, re.IGNORECASE)))


def field_at(fields: list[dict[str, object]], index: int) -> str:
    return str(fields[index].get("value", "")) if index < len(fields) else ""


def bullets_at(fields: list[dict[str, object]], index: int) -> list[str]:
    if index >= len(fields):
        return []
    values = [field_at(fields, index)] if field_at(fields, index) else []
    return values + [str(item) for item in fields[index].get("bullets", [])]


def split_semicolon_items(values: Iterable[str]) -> list[str]:
    return [
        clean_atom(clean_inline(item))
        for value in values
        for item in re.split(r"\s*;\s*", value)
        if clean_atom(clean_inline(item))
    ]


def split_heading(value: str) -> tuple[str, str]:
    cleaned = clean_inline(value)
    match = re.match(r"^([A-Z]+(?:-[A-Z]+)*-\d+)\s+[—–-]\s+(.+)$", cleaned)
    if match:
        return match.group(1), match.group(2)
    return "", cleaned


def parse_report(path: Path) -> Report:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    title = "Market Intelligence Report"
    run_id = ""
    report_time = ""
    crawl_window = ""
    sections: "OrderedDict[str, MarkdownSection]" = OrderedDict()
    current_section: MarkdownSection | None = None
    current_block: MarkdownBlock | None = None

    for raw in lines:
        if raw.startswith("# "):
            title = clean_inline(raw[2:])
            continue
        if raw.startswith("## "):
            current_section = MarkdownSection(clean_inline(raw[3:]))
            sections[current_section.heading] = current_section
            current_block = None
            continue
        if raw.startswith("### "):
            if current_section is None:
                raise ValueError(f"H3 appears before H2: {raw}")
            current_block = MarkdownBlock(clean_inline(raw[4:]))
            current_section.blocks.append(current_block)
            continue

        target = current_block.lines if current_block else (
            current_section.lines if current_section else None
        )
        if target is not None:
            target.append(raw)
        elif raw.lstrip().startswith("-"):
            item = clean_inline(raw.lstrip()[1:])
            if item.lower().startswith("run id:"):
                run_id = clean_inline(item.split(":", 1)[1])
            elif norm(item).startswith("thoi gian:"):
                report_time = clean_inline(item.split(":", 1)[1])
            elif norm(item).startswith("crawl 1 tuan:"):
                crawl_window = clean_inline(item.split(":", 1)[1])

    expected = ("executive summary", "findings", "approach")
    found = [norm(re.sub(r"^\d+\.\s*", "", key)) for key in sections]
    missing = [name for name in expected if name not in found]
    if missing:
        raise ValueError("Missing required report sections: " + ", ".join(missing))
    return Report(title, run_id, report_time, crawl_window, sections)


def section_by_name(report: Report, name: str) -> MarkdownSection:
    wanted = norm(name)
    for heading, section in report.sections.items():
        base = norm(re.sub(r"^\d+\.\s*", "", heading))
        if base == wanted:
            return section
    raise KeyError(name)


def parse_news(lines: Iterable[str]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    current: dict[str, object] | None = None
    for raw in lines:
        match = re.match(r"^\s*-\s+\*\*(NEWS-[^*]+)\*\*\s*$", raw)
        if match:
            if current:
                current["summary"] = " ".join(current.pop("summary_lines"))
                records.append(current)  # type: ignore[arg-type]
            news_id, title = split_heading(match.group(1))
            current = {"id": news_id, "title": title, "summary_lines": []}
            continue
        connection_match = re.match(
            r"^\s{2,}(?:-\s+)?Liên hệ\s+`?(SIGNAL-[A-Z0-9-]+)`?\s*:\s*(.+?)\s*$",
            raw,
            re.IGNORECASE,
        )
        if current and connection_match:
            if current.get("signal_connection"):
                raise ValueError(f"{current['id']} has more than one Signal connection")
            current["connection_signal_id"] = connection_match.group(1).upper()
            current["signal_connection"] = clean_inline(connection_match.group(2))
            continue
        source_match = re.match(r"^\s{2,}Nguồn:\s+\[([^\]]+)\]\((https?://[^)]+)\)\s*$", raw, re.IGNORECASE)
        if current and source_match:
            current["source_name"] = clean_inline(source_match.group(1))
            current["source_url"] = source_match.group(2)
            continue
        if current and raw.strip():
            text = clean_inline(re.sub(r"^\s*-\s+", "", raw))
            if text:
                current["summary_lines"].append(text)  # type: ignore[union-attr]
    if current:
        current["summary"] = " ".join(current.pop("summary_lines"))
        records.append(current)  # type: ignore[arg-type]
    return records


def parse_fields(lines: Iterable[str]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for raw in lines:
        if not raw.strip():
            continue
        top = re.match(r"^-\s+(.+)$", raw)
        nested = re.match(r"^\s{2,}-\s+(.+)$", raw)
        if top:
            content = clean_inline(top.group(1))
            if ":" in content:
                label, value = content.split(":", 1)
            else:
                label, value = "", content
            current = {"label": label.strip(), "value": value.strip(), "bullets": []}
            result.append(current)
        elif nested and current:
            current["bullets"].append(clean_inline(nested.group(1)))  # type: ignore[union-attr]
        elif current:
            extra = clean_inline(raw)
            current["value"] = (str(current["value"]) + " " + extra).strip()
    return result


def find_field(fields: list[dict[str, object]], *needles: str) -> dict[str, object]:
    for entry in fields:
        label = norm(str(entry["label"]))
        if any(norm(needle) in label for needle in needles):
            return entry
    return {"label": needles[0] if needles else "", "value": "", "bullets": []}


def field_text(fields: list[dict[str, object]], *needles: str) -> str:
    return str(find_field(fields, *needles)["value"])


def field_bullets(fields: list[dict[str, object]], *needles: str) -> list[str]:
    return list(find_field(fields, *needles)["bullets"])  # type: ignore[arg-type]


def enum_prefix(value: str, allowed: tuple[str, ...], field_name: str) -> str:
    cleaned = clean_atom(value).upper()
    match = re.match(rf"^({'|'.join(re.escape(item) for item in allowed)})\b", cleaned)
    if not match:
        raise ValueError(f"{field_name} must begin with one of {allowed}: {value}")
    return match.group(1)


def summary_bullets(section: MarkdownSection) -> list[str]:
    values = []
    for line in section.lines:
        match = re.match(r"^-\s+(.+)$", line)
        if match:
            values.append(clean_inline(match.group(1)))
    return values


def split_h4(lines: Iterable[str]) -> tuple[list[str], "OrderedDict[str, list[str]]"]:
    """Split one Finding H3 block into its leading fields and H4 subsections."""
    leading: list[str] = []
    subsections: "OrderedDict[str, list[str]]" = OrderedDict()
    current: list[str] | None = None
    for raw in lines:
        if raw.startswith("#### "):
            heading = clean_inline(raw[5:])
            current = []
            subsections[heading] = current
        elif current is None:
            leading.append(raw)
        else:
            current.append(raw)
    return leading, subsections


def subsection_by_name(subsections: "OrderedDict[str, list[str]]", name: str) -> list[str]:
    wanted = norm(name)
    for heading, lines in subsections.items():
        if norm(heading) == wanted:
            return lines
    raise ValueError(f"Missing Finding subsection: {name}")


def parse_bold_records(lines: Iterable[str]) -> list[tuple[str, list[dict[str, object]]]]:
    """Parse bold-bullet record headings and their nested field bullets."""
    records: list[tuple[str, list[dict[str, object]]]] = []
    heading = ""
    body: list[str] = []
    for raw in lines:
        match = re.match(r"^\s*-\s+\*\*([^*]+)\*\*\s*$", raw)
        if match:
            if heading:
                records.append((clean_inline(heading), parse_fields(body)))
            heading = match.group(1)
            body = []
            continue
        if heading and raw.strip():
            body.append(raw[2:] if raw.startswith("  ") else raw)
    if heading:
        records.append((clean_inline(heading), parse_fields(body)))
    return records


def record_heading(value: str) -> tuple[str, str]:
    item_id, title = split_heading(value)
    if item_id:
        return item_id, title
    ids = re.findall(r"\b(?:OT|PM|GAP|ACTION)-\d+\b", clean_inline(value), re.IGNORECASE)
    return (ids[0].upper(), clean_inline(value).replace(ids[0], "").strip(" —–-") if ids else clean_inline(value))


def chunks(values: list, size: int):
    for start in range(0, len(values), size):
        yield values[start : start + size]


def find_run_root(input_path: Path) -> Path:
    for candidate in (input_path.parent, *input_path.parents):
        if (candidate / "manifest.json").is_file() and (candidate / "reviews").is_dir():
            return candidate
    raise ValueError(
        "Cannot locate the WR3 run root. The input must belong to a run with manifest.json and reviews/."
    )


def validate_gates(run_root: Path) -> str:
    for kind, relative, key, expected in REQUIRED_GATES:
        path = run_root / relative
        if not path.is_file():
            raise ValueError(f"Required review is missing: {path}")
        if kind == "json":
            actual = str(json.loads(path.read_text(encoding="utf-8-sig")).get(key, ""))
        else:
            match = re.search(
                rf"(?mi)^\s*{re.escape(key)}\s*:\s*([^\s]+)\s*$",
                path.read_text(encoding="utf-8-sig"),
            )
            actual = match.group(1) if match else ""
        if actual.upper() != expected:
            raise ValueError(f"Gate not approved: {relative} has {key}={actual!r}")
    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8-sig"))
    return str(manifest.get("run_id") or run_root.name)


def load_approved_news_dates(run_root: Path) -> dict[str, str]:
    """Read approved News publication dates without changing the approved summary."""
    bundle_path = run_root / "artifacts" / "approved_news_bundle.json"
    if not bundle_path.is_file():
        return {}
    payload = json.loads(bundle_path.read_text(encoding="utf-8-sig"))
    dates: dict[str, str] = {}
    for record in payload.get("approved_news", []):
        if not isinstance(record, dict):
            continue
        news_id = clean_atom(str(record.get("news_id", ""))).upper()
        match = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(record.get("published_at", "")))
        if news_id and match:
            year, month, day = match.groups()
            dates[news_id] = f"{day}/{month}/{year}"
    return dates


def badge(text: str, style: str = "red") -> str:
    return f'<span class="mi-badge mi-badge--{style}">{esc(text)}</span>'


def bullet_list(values: list[str], css_class: str = "mi-list") -> str:
    return f'<ul class="{css_class}">' + "".join(f"<li>{esc(capitalize_initial(finding_board_copy(value)))}</li>" for value in values) + "</ul>"


def logo_data_uri(path: Path) -> str:
    suffix = path.suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/webp" if suffix == ".webp" else "image/svg+xml"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def font_data_uri(path: Path) -> str:
    return f"data:font/ttf;base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def image_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if data.startswith(b"\xff\xd8"):
        offset = 2
        while offset + 9 < len(data):
            if data[offset] != 0xFF:
                offset += 1
                continue
            marker = data[offset + 1]
            offset += 2
            if marker in {0xD8, 0xD9}:
                continue
            if offset + 2 > len(data):
                break
            segment_length = int.from_bytes(data[offset:offset + 2], "big")
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF} and offset + 7 < len(data):
                return int.from_bytes(data[offset + 5:offset + 7], "big"), int.from_bytes(data[offset + 3:offset + 5], "big")
            if segment_length < 2:
                break
            offset += segment_length
    return 0, 0


def discover_news_images(asset_dir: Path) -> dict[str, dict[str, object]]:
    images: dict[str, dict[str, object]] = {}
    if not asset_dir.is_dir():
        return images
    for path in sorted(asset_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} and path.stem.upper().startswith("NEWS-"):
            width, height = image_dimensions(path)
            ratio = width / height if width and height else 0
            layout = "side" if 0.85 <= ratio <= 1.15 else "top"
            images[path.stem.upper()] = {"uri": logo_data_uri(path), "width": width, "height": height, "layout": layout}
    return images


class SourceDeckOverlayParser(HTMLParser):
    """Extract presentation-only copy and emphasis from an existing generated deck."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cover_title = ""
        self.cover_subtitle = ""
        self.cover_date = ""
        self.current_signal = ""
        self.current_news: dict[str, object] | None = None
        self.news: dict[str, dict[str, object]] = {}
        self.capture_kind = ""
        self.capture_tag = ""
        self.capture_parts: list[str] = []

    @staticmethod
    def classes(attrs: dict[str, str | None]) -> set[str]:
        return set((attrs.get("class") or "").split())

    def start_capture(self, kind: str, tag: str):
        if self.capture_kind:
            raise ValueError(f"Nested source-deck capture is not supported: {self.capture_kind} -> {kind}")
        self.capture_kind = kind
        self.capture_tag = tag
        self.capture_parts = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]):
        attrs = dict(attrs_list)
        classes = self.classes(attrs)
        if tag == "h1" and not self.cover_title:
            self.start_capture("cover_title", tag)
        elif tag == "p" and "mi-cover-subtitle" in classes:
            self.start_capture("cover_subtitle", tag)
        elif tag == "p" and "mi-cover-date" in classes:
            self.start_capture("cover_date", tag)
        elif tag == "h2":
            self.start_capture("slide_h2", tag)
        elif tag == "article" and "mi-finding-news" in classes:
            self.current_news = {
                "signal_id": self.current_signal,
                "news_id": "",
                "subtitle": "",
                "published_date": "",
                "signal_connection": "",
                "article_title": "",
                "highlights": [],
            }
        elif self.current_news is not None and tag == "span" and "mi-badge" in classes:
            self.start_capture("news_id", tag)
        elif self.current_news is not None and tag == "h4":
            title_attr = clean_inline(attrs.get("title") or "")
            prefix = "Tiêu đề bài báo:"
            if title_attr.startswith(prefix):
                self.current_news["article_title"] = clean_inline(title_attr[len(prefix):])
            self.start_capture("news_subtitle", tag)
        elif self.current_news is not None and tag in {"p", "span"} and {"mi-published-date", "mi-board-published-date"} & classes:
            self.start_capture("news_published_date", tag)
        elif self.current_news is not None and tag in {"p", "div"} and {"mi-signal-connection", "mi-board-signal-connection"} & classes:
            self.start_capture("news_signal_connection", tag)
        elif self.current_news is not None and tag == "mark" and "mi-news-highlight" in classes:
            self.start_capture("news_highlight", tag)

    def handle_data(self, data: str):
        if self.capture_kind:
            self.capture_parts.append(data)

    def handle_endtag(self, tag: str):
        if self.capture_kind and tag == self.capture_tag:
            value = clean_inline("".join(self.capture_parts))
            kind = self.capture_kind
            self.capture_kind = ""
            self.capture_tag = ""
            self.capture_parts = []
            if kind == "cover_title":
                self.cover_title = value
            elif kind == "cover_subtitle":
                self.cover_subtitle = value
            elif kind == "cover_date":
                self.cover_date = value
            elif kind == "slide_h2":
                signal_ids = extract_ids(value, "SIGNAL")
                self.current_signal = signal_ids[0] if signal_ids else ""
            elif self.current_news is not None and kind == "news_id":
                self.current_news["news_id"] = clean_atom(value).upper()
            elif self.current_news is not None and kind == "news_subtitle":
                self.current_news["subtitle"] = value
            elif self.current_news is not None and kind == "news_published_date":
                prefix = "Xuất bản:"
                published_date = clean_inline(value[len(prefix):]) if value.startswith(prefix) else clean_inline(value)
                if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", published_date):
                    raise ValueError(f"Source-deck publication date is invalid: {value}")
                self.current_news["published_date"] = published_date
            elif self.current_news is not None and kind == "news_signal_connection":
                prefix = f"Liên hệ {self.current_news['signal_id']}:"
                # Accept both the legacy visible label and the current label-free
                # presentation. The approved Markdown remains authoritative.
                connection = value[len(prefix):] if value.startswith(prefix) else value
                self.current_news["signal_connection"] = clean_inline(connection)
            elif self.current_news is not None and kind == "news_highlight":
                highlights = self.current_news["highlights"]
                if isinstance(highlights, list):
                    highlights.append(value)
        if tag == "article" and self.current_news is not None:
            news_id = str(self.current_news.get("news_id", ""))
            if not re.fullmatch(r"NEWS-[A-Z0-9-]+", news_id):
                raise ValueError(f"Source deck contains an invalid News card ID: {news_id}")
            if news_id in self.news:
                raise ValueError(f"Source deck contains duplicate News card: {news_id}")
            self.news[news_id] = self.current_news
            self.current_news = None


def load_presentation_overlay(path: Path) -> PresentationOverlay:
    if not path.is_file():
        raise ValueError(f"Source deck not found: {path}")
    parser = SourceDeckOverlayParser()
    parser.feed(path.read_text(encoding="utf-8-sig"))
    parser.close()
    if not parser.news:
        raise ValueError("Source deck must contain editorial News cards")
    return PresentationOverlay(path, parser.cover_title, parser.cover_subtitle, parser.cover_date, parser.news)


def render_news_highlights(summary: str, highlights: list[str], news_id: str) -> str:
    matches: list[tuple[int, int]] = []
    for phrase in highlights:
        start = summary.find(phrase)
        if start < 0:
            raise ValueError(f"{news_id} highlight is not an exact substring of its approved summary: {phrase}")
        matches.append((start, start + len(phrase)))
    matches.sort()
    for previous, current in zip(matches, matches[1:]):
        if current[0] < previous[1]:
            raise ValueError(f"{news_id} highlights must not overlap")
    parts: list[str] = []
    cursor = 0
    for start, end in matches:
        parts.append(esc(summary[cursor:start]))
        parts.append(f'<mark class="mi-board-highlight">{esc(summary[start:end])}</mark>')
        cursor = end
    parts.append(esc(summary[cursor:]))
    return "".join(parts)


class HtmlDeckBuilder:
    def __init__(self, report: Report, logo_uri: str, run_id: str, excluded_news_ids: set[str] | None = None, news_images: dict[str, dict[str, object]] | None = None, overlay: PresentationOverlay | None = None, news_dates: dict[str, str] | None = None):
        self.report = report
        self.logo_uri = logo_uri
        self.run_id = report.run_id or run_id
        self.excluded_news_ids = excluded_news_ids or set()
        self.news_images = news_images or {}
        self.overlay = overlay
        self.news_dates = news_dates or {}
        self.embedded_news_images: set[str] = set()
        self.slides: list[Slide] = []

    def editorial_news_copy(self, item: dict[str, str], signal_id: str) -> tuple[str, str, str, str]:
        news_id = item["id"].upper()
        connection_signal_id = clean_atom(item.get("connection_signal_id", "")).upper()
        signal_connection = clean_inline(item.get("signal_connection", ""))
        if connection_signal_id != signal_id.upper():
            raise ValueError(
                f"Broken Markdown News lineage for {news_id}: expected {signal_id}, "
                f"found {connection_signal_id or 'missing connection'}"
            )
        if not signal_connection or len(signal_connection) > 180:
            raise ValueError(f"{news_id} requires a Markdown Signal connection of at most 180 characters")
        if self.overlay is None:
            return item["title"], signal_connection, self.news_dates.get(news_id, ""), esc(item["summary"])
        record = self.overlay.news.get(news_id)
        if record is None:
            raise ValueError(f"Source deck is missing News card: {news_id}")
        source_signal = clean_atom(str(record.get("signal_id", ""))).upper()
        if source_signal != signal_id.upper():
            raise ValueError(f"Broken source-deck News lineage for {news_id}: expected {signal_id}, found {source_signal}")
        article_title = clean_inline(str(record.get("article_title", "")))
        if article_title and norm(article_title) != norm(item["title"]):
            raise ValueError(f"Source-deck article title mismatch for {news_id}")
        subtitle = clean_inline(str(record.get("subtitle", "")))
        if not subtitle or len(subtitle) > 300:
            raise ValueError(f"{news_id} requires a source-deck title of at most 300 characters")
        if norm(subtitle) != norm(item["title"]):
            raise ValueError(f"{news_id} source-deck title must match the approved article title")
        overlay_connection = clean_inline(str(record.get("signal_connection", "")))
        if not overlay_connection or len(overlay_connection) > 180:
            raise ValueError(f"{news_id} requires a source-deck Signal connection of at most 180 characters")
        if norm(overlay_connection) != norm(signal_connection):
            raise ValueError(f"{news_id} source-deck Signal connection differs from the approved Markdown")
        published_date = clean_inline(str(record.get("published_date", "")))
        if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", published_date):
            raise ValueError(f"{news_id} requires a source-deck publication date in dd/mm/yyyy format")
        raw_highlights = record.get("highlights")
        if not isinstance(raw_highlights, list) or not 1 <= len(raw_highlights) <= 3:
            raise ValueError(f"{news_id} requires one to three source-deck highlights")
        highlights = [clean_inline(str(value)) for value in raw_highlights]
        if any(not value for value in highlights):
            raise ValueError(f"{news_id} contains an empty source-deck highlight")
        return subtitle, signal_connection, published_date, render_news_highlights(item["summary"], highlights, news_id)

    @property
    def logo(self) -> str:
        return (
            '<div class="mi-logo">'
            f'<img src="{self.logo_uri}" alt="Vinsmart Future">'
            "</div>"
        )

    def add_standard(self, section: str, title: str, subtitle: str, body: str, classes: str = ""):
        subtitle_markup = f'<p class="mi-subtitle">{esc(subtitle)}</p>' if subtitle else ""
        markup = f"""
          <header class="mi-slide-header">
            <div class="mi-header-copy">
              <p class="mi-eyebrow">{esc(section)}</p>
              <h2>{keep_phrase_groups(title)}</h2>
              {subtitle_markup}
            </div>
            {self.logo}
          </header>
          <div class="mi-slide-body">{body}</div>
        """
        self.slides.append(Slide(markup, section, title, classes))

    def build_cover(self):
        cover_background_uri = logo_data_uri(COVER_BACKGROUND_PATH)
        markup = f"""
          <div class="mi-cover-background" aria-hidden="true"><img src="{cover_background_uri}" alt=""></div>
          <div class="mi-cover-copy">
            <p class="mi-eyebrow">VSF MARKET INTELLIGENCE</p>
            <h1>Market Intelligence<br>Report</h1>
            <p class="mi-cover-subtitle">Phòng Nghiên cứu thị trường và Trải nghiệm khách hàng<br><span class="mi-cover-subtitle-line2">• Khối Smart City</span></p>
            <div class="mi-cover-rule"></div>
            <p class="mi-cover-date">{esc(presentation_cover_date(self.report.crawl_window or 'Không được cung cấp'))}</p>
          </div>
          <div class="mi-cover-brand">{self.logo}</div>
        """
        self.slides.append(Slide(markup, "Cover", "Market Intelligence Report", "mi-cover mi-cover-board"))

    def build_agenda(self):
        rows = (
            ("01", "News", "Tin đã được KEEP"),
            ("02", "Signals", "Tín hiệu tổng hợp"),
            ("03", "Opportunity / Threat", "Cơ hội và thách thức"),
            ("04", "Product Mapping", "Nhu cầu thị trường"),
            ("05", "Product Gaps", "Khoảng trống năng lực"),
            ("06", "Actions", "Hành động đã duyệt"),
            ("07", "Summary", "Điểm chốt điều hành"),
        )
        cards = "".join(
            f"""
            <article class="mi-agenda-item">
              {badge(number)}
              <div><h3>{esc(title)}</h3><p>{esc(caption)}</p></div>
            </article>
            """ for number, title, caption in rows
        )
        body = f"""
          <div class="mi-agenda-grid">{cards}</div>
          <p class="mi-provenance">Mọi nội dung trên slide được lấy nguyên từ báo cáo đã qua các bước review bắt buộc.</p>
        """
        self.add_standard("NỘI DUNG", "Từ tín hiệu thị trường đến hành động", "7 lớp nội dung có lineage", body, "mi-agenda")

    def build_news(self):
        section = section_by_name(self.report, "News")
        categories = [(block.heading, parse_news(block.lines)) for block in section.blocks]
        total = sum(len(records) for _, records in categories)
        overview = "".join(
            f"""
            <article class="mi-stat-card">
              <strong>{len(records):02d}</strong>
              <h3>{esc(name)}</h3>
              <div class="mi-mini-rule"></div>
              <p>{'<br>'.join(esc(record['id']) for record in records)}</p>
            </article>
            """ for name, records in categories
        )
        self.add_standard(
            "01 • NEWS",
            "Bức tranh tin tức đã được phê duyệt",
            f"{total} tin • {len(categories)} nhóm nguồn",
            f'<div class="mi-grid mi-grid--4">{overview}</div>',
            "mi-news-overview",
        )

        for category, records in categories:
            for page_index, page in enumerate(chunks(records, 3), 1):
                suffix = f" • {page_index}" if len(records) > 3 else ""
                cards = "".join(
                    f"""
                    <article class="mi-news-card">
                      {badge(record['id'])}
                      <h3>{esc(record['title'])}</h3>
                      <div class="mi-mini-rule"></div>
                      <p>{esc(record['summary'])}</p>
                    </article>
                    """ for record in page
                )
                count_class = f"mi-grid--{len(page)}"
                self.add_standard(
                    "01 • NEWS",
                    category + suffix,
                    f"{len(records)} tin đã được KEEP trong nhóm này",
                    f'<div class="mi-grid {count_class}">{cards}</div>',
                    "mi-news-detail",
                )

    def build_signals(self):
        section = section_by_name(self.report, "Signals")
        for page_index, page in enumerate(chunks(section.blocks, 2), 1):
            cards = []
            for block in page:
                item_id, title = split_heading(block.heading)
                fields = parse_fields(block.lines)
                body = field_text(fields, "Nội dung")
                lineage = clean_atom(field_text(fields, "News liên quan"))
                cards.append(f"""
                  <article class="mi-signal-card">
                    {badge(item_id)}
                    <h3>{esc(title)}</h3>
                    <p class="mi-body-copy">{esc(body)}</p>
                    <div class="mi-lineage"><span>LINEAGE</span><strong>{esc(lineage)}</strong></div>
                  </article>
                """)
            self.add_standard(
                "02 • SIGNALS",
                "Tín hiệu thị trường",
                f"Trang {page_index} • Tổng {len(section.blocks)} tín hiệu",
                f'<div class="mi-grid mi-grid--2">{"".join(cards)}</div>',
                "mi-signals",
            )

    def build_ot(self):
        section = section_by_name(self.report, "Opportunities & Threats")
        for page_index, page in enumerate(chunks(section.blocks, 4), 1):
            cards = []
            for block in page:
                item_id, kind = split_heading(block.heading)
                fields = parse_fields(block.lines)
                body = field_text(fields, "Nội dung")
                priority = clean_atom(field_text(fields, "Mức độ quan trọng"))
                lineage = clean_atom(field_text(fields, "Signal liên quan"))
                cards.append(f"""
                  <article class="mi-ot-card">
                    <div class="mi-badge-row">
                      {badge(item_id, 'neutral')}{badge(kind, 'deep' if norm(kind) == 'threat' else 'red')}{badge(priority, 'outline')}
                    </div>
                    <p>{esc(body)}</p>
                    <div class="mi-lineage mi-lineage--inline"><span>Signal liên quan</span><strong>{esc(lineage)}</strong></div>
                  </article>
                """)
            self.add_standard(
                "03 • OPPORTUNITY / THREAT",
                "Cơ hội và thách thức",
                f"Trang {page_index} • Chỉ gồm O/T đã APPROVE",
                f'<div class="mi-grid mi-grid--2 mi-grid--ot">{"".join(cards)}</div>',
                "mi-ot",
            )

    def build_mapping(self):
        section = section_by_name(self.report, "Product Mapping")
        for block in section.blocks:
            item_id, title = split_heading(block.heading)
            fields = parse_fields(block.lines)
            lineage = clean_atom(field_text(fields, "O/T liên quan"))
            problem = field_text(fields, "Vấn đề thị trường")
            capabilities = field_bullets(fields, "Năng lực bắt buộc")
            customer = field_text(fields, "Khách hàng mục tiêu")
            body = f"""
              <div class="mi-record-tag">{badge(item_id)}</div>
              <div class="mi-mapping-layout">
                <div class="mi-stack">
                  <article class="mi-panel mi-panel--compact">
                    <h3>VẤN ĐỀ THỊ TRƯỜNG</h3><p>{esc(problem)}</p>
                  </article>
                  <article class="mi-panel mi-panel--grow">
                    <h3>NĂNG LỰC BẮT BUỘC</h3>{bullet_list(capabilities)}
                  </article>
                </div>
                <aside class="mi-panel mi-panel--soft">
                  <h3>LINEAGE</h3><strong>{esc(lineage)}</strong>
                  <div class="mi-mini-rule"></div>
                  <h3>KHÁCH HÀNG MỤC TIÊU</h3><p>{esc(customer)}</p>
                </aside>
              </div>
            """
            self.add_standard("04 • PRODUCT MAPPING", title, "Nhóm giải pháp trung lập theo nhu cầu thị trường", body, "mi-mapping")

    def build_gaps(self):
        section = section_by_name(self.report, "Product Gaps")
        for block in section.blocks:
            item_id, title = split_heading(block.heading)
            fields = parse_fields(block.lines)
            lineage = clean_atom(field_text(fields, "Product Mapping liên quan"))
            product = field_text(fields, "Sản phẩm VSF liên quan")
            capability_status = clean_atom(field_text(fields, "Trạng thái capability"))
            missing = field_bullets(fields, "Capability còn thiếu")
            gap = clean_atom(field_text(fields, "Mức độ gap"))
            body = f"""
              <div class="mi-record-tag">{badge(item_id)}</div>
              <div class="mi-gap-layout">
                <article class="mi-panel">
                  <h3>CAPABILITY CÒN THIẾU</h3>{bullet_list(missing)}
                </article>
                <aside class="mi-panel mi-panel--soft mi-facts">
                  <div><span>GAP LEVEL</span>{badge(gap, 'deep' if norm(gap) == 'high' else 'red')}</div>
                  <div><span>CAPABILITY STATUS</span><strong>{esc(capability_status)}</strong></div>
                  <div><span>PRODUCT MAPPING</span><strong>{esc(lineage)}</strong></div>
                  <div><span>SẢN PHẨM VSF LIÊN QUAN</span><p>{esc(product)}</p></div>
                </aside>
              </div>
            """
            self.add_standard("05 • PRODUCT GAPS", title, "Đối chiếu capability đã qua manual review", body, "mi-gaps")

    def build_actions(self):
        section = section_by_name(self.report, "Actions")
        for block in section.blocks:
            item_id, priority = split_heading(block.heading)
            fields = parse_fields(block.lines)
            lineage = clean_atom(field_text(fields, "Product Gap liên quan"))
            action = field_text(fields, "Hành động đề xuất")
            next_step = field_text(fields, "Bước tiếp theo")
            outcome = field_text(fields, "Kết quả mong đợi")
            body = f"""
              <article class="mi-action-hero">
                <h3>HÀNH ĐỘNG ĐỀ XUẤT</h3><p>{esc(action)}</p>
              </article>
              <div class="mi-action-grid">
                <article class="mi-panel"><h3>BƯỚC TIẾP THEO</h3><p>{esc(next_step)}</p></article>
                <article class="mi-panel"><h3>KẾT QUẢ MONG ĐỢI</h3><p>{esc(outcome)}</p></article>
              </div>
            """
            self.add_standard(
                "06 • ACTIONS",
                f"{item_id} • {priority}",
                f"Lineage: {lineage} • Chỉ gồm Action đã APPROVE",
                body,
                "mi-actions",
            )

    def build_signal_lineage(self):
        news = {}
        for category in section_by_name(self.report, "News").blocks:
            for record in parse_news(category.lines):
                news[record["id"]] = record

        ots_by_signal = {}
        for block in section_by_name(self.report, "Opportunities & Threats").blocks:
            ot_id, kind = split_heading(block.heading)
            fields = parse_fields(block.lines)
            for signal_id in extract_ids(field_at(fields, 2), "SIGNAL"):
                ots_by_signal.setdefault(signal_id, []).append((ot_id, kind, fields))

        for block in section_by_name(self.report, "Signals").blocks:
            signal_id, title = split_heading(block.heading)
            fields = parse_fields(block.lines)
            related_news = [
                news[item_id]
                for item_id in extract_ids(field_at(fields, 1), "NEWS")
                if item_id in news and item_id not in self.excluded_news_ids
            ]
            news_cards = "".join(
                f'<article class="mi-lineage-news">{badge(item["id"], "neutral")}<h4>{esc(item["title"])}</h4>'
                f'<p>{esc(item["summary"])}</p>'
                + (
                    f'<a class="mi-news-cite" href="{esc(item["source_url"])}" target="_blank" rel="noopener" title="{esc(item["source_url"])}">Nguồn: {esc(item["source_name"])} ↗</a>'
                    if item.get("source_name") and item.get("source_url") else ""
                )
                + '</article>'
                for item in related_news
            )
            ot_cards = "".join(
                f'<article class="mi-lineage-ot mi-lineage-ot--{"threat" if norm(kind) == "threat" else "opportunity"}">'
                f'<div class="mi-badge-row">{badge(ot_id, "neutral")}{badge(kind, "deep" if norm(kind) == "threat" else "red")}'
                f'{badge(clean_atom(field_at(ot_fields, 1)), "outline")}</div>'
                f'<p>{esc(field_at(ot_fields, 0))}</p></article>'
                for ot_id, kind, ot_fields in ots_by_signal.get(signal_id, [])
            )
            body = f"""
              <div class="mi-signal-lineage-layout">
                <div class="mi-signal-evidence">
                  <article class="mi-signal-hero"><h3>Signal</h3><p>{esc(field_at(fields, 0))}</p></article>
                  <h3 class="mi-column-title">News liên quan</h3><div class="mi-news-strip">{news_cards}</div>
                </div>
                <aside class="mi-ot-stack"><h3 class="mi-column-title">Opportunity / Threat</h3>{ot_cards}</aside>
              </div>"""
            self.add_standard("SIGNAL + NEWS + O/T", f"{signal_id} — {title}", "Signal, toàn bộ News lineage và O/T liên quan trên cùng slide", body, "mi-signal-lineage")

    def build_action_guide(self):
        section = section_by_name(self.report, "Actions")
        guide_heading = norm("Cách đọc hướng phản hồi")
        guide = next((block for block in section.blocks if norm(block.heading) == guide_heading), None)
        if guide is None:
            return

        counts: dict[str, int] = {}
        for block in section.blocks:
            action_id, _ = split_heading(block.heading)
            if not action_id:
                continue
            response = clean_atom(field_text(parse_fields(block.lines), "Hướng phản hồi")).upper()
            if response:
                counts[response] = counts.get(response, 0) + 1

        cards = []
        for entry in parse_fields(guide.lines):
            response = clean_inline(str(entry.get("label", ""))).upper()
            description = str(entry.get("value", ""))
            if not response:
                continue
            style = "deep" if response == "VALIDATE" else "neutral" if response == "MONITOR" else "red"
            cards.append(f"""
              <article class="mi-action-guide-card mi-action-guide-card--{response.lower()}">
                <div class="mi-badge-row">{badge(response, style)}{badge(f'{counts.get(response, 0)} Action', 'outline')}</div>
                <p>{esc(description)}</p>
              </article>
            """)

        self.add_standard(
            "06 • ACTIONS",
            "Cách đọc hướng phản hồi",
            "Bốn mức phản hồi cho biết độ sẵn sàng và mục tiêu của bước tiếp theo",
            f'<div class="mi-action-guide-grid">{"".join(cards)}</div>',
            "mi-action-guide",
        )

    def build_products(self):
        gaps_by_pm = {}
        for block in section_by_name(self.report, "Product Gaps").blocks:
            gap_id, _ = split_heading(block.heading)
            gap_id = gap_id or clean_inline(block.heading)
            fields = parse_fields(block.lines)
            for pm_id in extract_ids(field_at(fields, 0), "PM"):
                gaps_by_pm[pm_id] = (gap_id, fields)

        actions_by_gap = {}
        for block in section_by_name(self.report, "Actions").blocks:
            action_id, priority = split_heading(block.heading)
            if not action_id:
                continue
            fields = parse_fields(block.lines)
            response = clean_atom(field_text(fields, "Hướng phản hồi")).upper()
            for gap_id in extract_ids(field_text(fields, "Product Gap liên quan"), "GAP"):
                actions_by_gap.setdefault(gap_id, []).append((action_id, priority, response, fields))

        for index, block in enumerate(section_by_name(self.report, "Product Mapping").blocks, 1):
            pm_id, title = split_heading(block.heading)
            pm = parse_fields(block.lines)
            gap_id, gap = gaps_by_pm.get(pm_id, ("—", []))
            actions = "".join(
                f'<article class="mi-product-action"><div class="mi-badge-row">{badge(action_id)}'
                f'{badge(response, "deep" if response == "VALIDATE" else "neutral" if response == "MONITOR" else "red")}'
                f'{badge(priority, "outline")}</div>'
                f'<p><strong>Hành động:</strong> {esc(field_text(action, "Hành động đề xuất"))}</p>'
                f'<p><strong>Bước tiếp:</strong> {esc(field_text(action, "Bước tiếp theo"))}</p>'
                f'<p><strong>Kết quả:</strong> {esc(field_text(action, "Kết quả mong đợi"))}</p></article>'
                for action_id, priority, response, action in actions_by_gap.get(gap_id, [])
            ) or '<p>Không có Action APPROVE liên quan.</p>'
            body = f"""
              <div class="mi-product-triad">
                <section class="mi-product-col mi-product-map"><h3>Map</h3>{badge(pm_id)}
                  <p><strong>Liên quan O/T:</strong> {esc(clean_atom(field_at(pm, 0)))}</p>
                  <p><strong>Vấn đề:</strong> {esc(field_at(pm, 1))}</p>
                  <p><strong>Khách hàng:</strong> {esc(field_at(pm, 3))}</p>
                </section>
                <section class="mi-product-col mi-product-gap"><h3>Gap</h3>{badge(gap_id, "neutral")}
                  <p><strong>Sản phẩm VSF:</strong> {esc(field_at(gap, 1))}</p>
                  <p><strong>Status:</strong> {esc(clean_atom(field_at(gap, 2)))}</p>
                  <p><strong>Gap level:</strong> {esc(clean_atom(field_at(gap, 4)))}</p>
                  <div class="mi-missing-capabilities"><strong>Thiếu chính:</strong>{bullet_list(split_semicolon_items(bullets_at(gap, 3)), "mi-missing-list")}</div>
                </section>
                <section class="mi-product-col mi-product-actions"><h3>Action</h3>{actions}</section>
              </div>"""
            self.add_standard("GIẢI PHÁP • MAP + GAP + ACTION", f"NHÓM GIẢI PHÁP {index:02d} — {title}", f"{pm_id} / {gap_id} / Action đã APPROVE", body, "mi-product-slide")

    def build_executive_summary(self):
        section = section_by_name(self.report, "Executive Summary")
        rows = []
        seen_signals: set[str] = set()
        seen_actions: set[str] = set()
        for block in section.blocks:
            signal_ids = extract_ids(block.heading, "SIGNAL")
            action_ids = extract_ids(block.heading, "ACTION")
            if len(signal_ids) != 1 or len(action_ids) != 1:
                raise ValueError(f"Executive Summary must map exactly one Signal to one Action: {block.heading}")
            signal_id, action_id = signal_ids[0], action_ids[0]
            if signal_id in seen_signals or action_id in seen_actions:
                raise ValueError(f"Executive Summary mapping is not one-to-one: {block.heading}")
            seen_signals.add(signal_id)
            seen_actions.add(action_id)
            fields = parse_fields(block.lines)
            signal = finding_board_copy(field_text(fields, "Signal"))
            action = finding_board_copy(field_text(fields, "Action"))
            editorial = EXECUTIVE_SUMMARY_EDITORIAL.get((signal_id, action_id))
            if editorial:
                signal = normalize_customer_copy(editorial["signal"])
                action = normalize_customer_copy(editorial["action"])
                signal_markup = render_exact_bold_phrases(
                    signal,
                    editorial["signal_bold"],
                    f"{signal_id} Executive Summary",
                )
                action_markup = render_exact_bold_phrases(
                    action,
                    editorial["action_bold"],
                    f"{action_id} Executive Summary",
                )
            else:
                signal_markup = esc(signal)
                action_markup = esc(action)
            response = enum_prefix(
                field_text(fields, "Hướng phản hồi"),
                ("PREPARE", "VALIDATE", "MONITOR", "ACT"),
                "Executive Summary response",
            )
            priority = enum_prefix(
                field_text(fields, "Priority"),
                ("CRITICAL", "HIGH", "MEDIUM", "LOW"),
                "Executive Summary priority",
            )
            rows.append(f"""
              <article class="mi-exec-row">
                <div class="mi-exec-signal"><div class="mi-badge-row">{badge(signal_id, 'neutral')}</div><p>{signal_markup}</p></div>
                <div class="mi-exec-technology">
                  <strong>Giải pháp công nghệ</strong>
                  <span class="mi-fill-placeholder mi-exec-technology-placeholder" data-ppt-placeholder="executive-technology-solution-{esc(signal_id.lower())}" data-ppt-placeholder-prompt="Team QLSP điền giải pháp công nghệ cho {esc(signal_id)}" aria-label="Team QLSP điền giải pháp công nghệ cho {esc(signal_id)}"></span>
                </div>
                <div class="mi-exec-arrow" aria-hidden="true">→</div>
                <div class="mi-exec-action"><p>{action_markup}</p></div>
              </article>
            """)
        findings_count = len(section_by_name(self.report, "Findings").blocks)
        if len(rows) != findings_count:
            raise ValueError(f"Executive Summary has {len(rows)} mappings but Findings has {findings_count} Signals")
        self.add_standard(
            "01 • EXECUTIVE SUMMARY",
            "Điểm nhấn thị trường và Đề xuất hành động",
            "",
            f'<div class="mi-exec-list">{"".join(rows)}</div>',
            "mi-executive-summary",
        )

    def build_findings(self):
        section = section_by_name(self.report, "Findings")
        for index, block in enumerate(section.blocks, 1):
            signal_id, title = split_heading(block.heading)
            title = finding_board_copy(title)
            if not signal_id:
                raise ValueError(f"Finding heading must start with SIGNAL ID: {block.heading}")
            leading, subsections = split_h4(block.lines)
            signal = finding_board_copy(field_text(parse_fields(leading), "Signal"))
            news_records = [
                item for item in parse_news(subsection_by_name(subsections, "News"))
                if item["id"] not in self.excluded_news_ids
            ]
            ot_records = parse_bold_records(subsection_by_name(subsections, "Opportunity / Threat"))
            map_records = parse_bold_records(subsection_by_name(subsections, "Product Mapping"))
            gap_records = parse_bold_records(subsection_by_name(subsections, "Product Gap"))
            action_records = parse_bold_records(subsection_by_name(subsections, "Action"))
            if len(map_records) != 1 or len(gap_records) != 1 or len(action_records) != 1:
                raise ValueError(f"{signal_id} must contain exactly one Map, one Gap, and one Action")

            image_id = next((item["id"] for item in news_records if item["id"] in self.news_images), "")
            if not image_id:
                raise ValueError(f"{signal_id} requires one local source image for a related News record")
            news_cards = []
            for item in news_records:
                image_markup = ""
                image_class = ""
                if item["id"] == image_id:
                    news_image = self.news_images[item["id"]]
                    image_class = f' mi-finding-news--image mi-finding-news--image-{news_image["layout"]}'
                    self.embedded_news_images.add(item["id"])
                    image_markup = (
                        f'<a class="mi-news-image" href="{esc(item.get("source_url", ""))}" target="_blank" rel="noopener" title="{esc(item.get("source_url", ""))}">'
                        f'<img src="{news_image["uri"]}" width="{news_image["width"]}" height="{news_image["height"]}" alt="Ảnh nguồn cho {esc(item["id"])}"></a>'
                    )
                citation = (
                    f'<a class="mi-news-cite" href="{esc(item["source_url"])}" target="_blank" rel="noopener" title="{esc(item["source_url"])}">Nguồn: {esc(item["source_name"])} ↗</a>'
                    if item.get("source_name") and item.get("source_url") else ""
                )
                news_cards.append(
                    f'<article class="mi-finding-news{image_class}">{image_markup}<div class="mi-finding-news-copy">'
                    f'{badge(item["id"], "neutral")}<h4>{esc(item["title"])}</h4><p>{esc(item["summary"])}</p>{citation}</div></article>'
                )

            ot_cards = []
            for heading, fields in ot_records:
                ot_id, kind = record_heading(heading)
                priority = clean_atom(field_text(fields, "Mức độ quan trọng"))
                related = extract_ids(field_text(fields, "Signal liên quan"), "SIGNAL")
                if related != [signal_id]:
                    raise ValueError(f"Broken O/T lineage for {ot_id}: expected {signal_id}, found {related}")
                ot_cards.append(
                    f'<article class="mi-finding-ot mi-finding-ot--{"threat" if norm(kind) == "threat" else "opportunity"}">'
                    f'<div class="mi-badge-row">{badge(ot_id, "neutral")}{badge(kind, "deep" if norm(kind) == "threat" else "red")}{badge(priority, "outline")}</div>'
                    f'<p>{esc(field_text(fields, "Nội dung"))}</p></article>'
                )

            map_heading, map_fields = map_records[0]
            pm_id, pm_title = record_heading(map_heading)
            gap_heading, gap_fields = gap_records[0]
            gap_id, _ = record_heading(gap_heading)
            action_heading, action_fields = action_records[0]
            action_id, priority = record_heading(action_heading)
            response = clean_atom(field_text(action_fields, "Hướng phản hồi")).upper()
            if extract_ids(field_text(gap_fields, "Product Mapping liên quan"), "PM") != [pm_id]:
                raise ValueError(f"Broken Gap lineage for {gap_id}")
            if extract_ids(field_text(action_fields, "Product Gap liên quan"), "GAP") != [gap_id]:
                raise ValueError(f"Broken Action lineage for {action_id}")

            map_body = f"""
              <article class="mi-decision-card mi-decision-map"><div class="mi-decision-head"><span>MAP</span>{badge(pm_id)}</div>
                <h4>{esc(pm_title)}</h4><p><strong>Vấn đề:</strong> {esc(field_text(map_fields, 'Vấn đề thị trường'))}</p>
                <p><strong>Khách hàng:</strong> {esc(field_text(map_fields, 'Khách hàng mục tiêu'))}</p></article>"""
            gap_body = f"""
              <article class="mi-decision-card mi-decision-gap"><div class="mi-decision-head"><span>GAP</span>{badge(gap_id, 'neutral')}</div>
                <div class="mi-badge-row">{badge(clean_atom(field_text(gap_fields, 'Trạng thái capability')), 'neutral')}{badge(clean_atom(field_text(gap_fields, 'Mức độ gap')), 'outline')}</div>
                <p><strong>VSF:</strong> {esc(field_text(gap_fields, 'Sản phẩm VSF liên quan'))}</p>
                <div class="mi-gap-missing"><strong>Thiếu:</strong>{bullet_list(split_semicolon_items([field_text(gap_fields, 'Capability còn thiếu')]), 'mi-gap-missing-list')}</div></article>"""
            action_body = f"""
              <article class="mi-decision-card mi-decision-action"><div class="mi-decision-head"><span>ACTION</span><div>{badge(action_id)}{badge(response, 'deep' if response == 'VALIDATE' else 'neutral' if response == 'MONITOR' else 'red')}{badge(priority, 'outline')}</div></div>
                <p><strong>Đề xuất:</strong> {esc(field_text(action_fields, 'Hành động đề xuất'))}</p>
                <p><strong>Bước tiếp:</strong> {esc(field_text(action_fields, 'Bước tiếp theo'))}</p>
                <p><strong>Kết quả:</strong> {esc(field_text(action_fields, 'Kết quả mong đợi'))}</p></article>"""

            evidence_body = f"""
              <article class="mi-finding-signal"><span>SIGNAL</span><p>{esc(signal)}</p></article>
              <section class="mi-news-section"><h3>News</h3><div class="mi-finding-news-grid mi-finding-news-grid--{len(news_cards)}">{"".join(news_cards)}</div></section>
            """
            self.add_standard(
                f"02 • FINDING {index:02d}A • SIGNAL + NEWS",
                f"{signal_id} — {title}",
                "Bằng chứng thị trường trực tiếp cho Signal đã được duyệt",
                evidence_body,
                "mi-finding mi-finding-news-slide",
            )
            decision_body = f"""
              <div class="mi-decision-four">
                <section class="mi-decision-panel mi-decision-ot"><div class="mi-panel-title"><span>OPPORTUNITY / THREAT</span><small>{esc(signal_id)}</small></div><div class="mi-finding-ot-stack">{"".join(ot_cards)}</div></section>
                {map_body}
                {gap_body}
                {action_body}
              </div>
            """
            self.add_standard(
                f"02 • FINDING {index:02d}B • DECISION LINEAGE",
                f"{signal_id} — {title}",
                "Opportunity / Threat → Product Mapping → Product Gap → Approved Action",
                decision_body,
                "mi-finding mi-finding-decision-slide",
            )

    def build_cover_board(self):
        self.build_cover()

    def build_cover_from_overlay(self):
        self.build_cover()

    def build_findings_board(self):
        section = section_by_name(self.report, "Findings")
        for index, block in enumerate(section.blocks, 1):
            signal_id, title = split_heading(block.heading)
            title = finding_board_copy(title)
            if not signal_id:
                raise ValueError(f"Finding heading must start with SIGNAL ID: {block.heading}")

            leading, subsections = split_h4(block.lines)
            signal = field_text(parse_fields(leading), "Signal")
            news_records = [
                item for item in parse_news(subsection_by_name(subsections, "News"))
                if item["id"] not in self.excluded_news_ids
            ]
            ot_records = parse_bold_records(subsection_by_name(subsections, "Opportunity / Threat"))
            map_records = parse_bold_records(subsection_by_name(subsections, "Product Mapping"))
            gap_records = parse_bold_records(subsection_by_name(subsections, "Product Gap"))
            action_records = parse_bold_records(subsection_by_name(subsections, "Action"))
            if len(map_records) != 1 or len(gap_records) != 1 or len(action_records) != 1:
                raise ValueError(f"{signal_id} must contain exactly one Map, one Gap, and one Action")

            image_id = next((item["id"] for item in news_records if item["id"] in self.news_images), "")
            if not image_id:
                related = ", ".join(item["id"] for item in news_records) or "none"
                raise ValueError(f"{signal_id} requires one local source image; related News: {related}")
            singleton_card_indexes = (
                {0} if len(news_records) in {1, 3}
                else set(range(len(news_records))) if len(news_records) == 2
                else set()
            )
            inline_image_ids: set[str] = set()
            news_cards = []
            for news_index, item in enumerate(news_records):
                editorial_subtitle, signal_connection, published_date, highlighted_summary = self.editorial_news_copy(item, signal_id)
                signal_connection = finding_connection_copy(signal_connection)
                inline_image = ""
                if news_index in singleton_card_indexes and item["id"] in self.news_images:
                    news_image = self.news_images[item["id"]]
                    inline_image_ids.add(item["id"])
                    self.embedded_news_images.add(item["id"])
                    inline_image = (
                        f'<a class="mi-board-news-inline-image mi-board-news-inline-image--{news_image["layout"]}" data-news-id="{esc(item["id"])}" '
                        f'href="{esc(item.get("source_url", ""))}" target="_blank" rel="noopener" '
                        f'title="{esc(item.get("source_url", ""))}">'
                        f'<img src="{news_image["uri"]}" width="{news_image["width"]}" height="{news_image["height"]}" '
                        f'alt="Ảnh nguồn cho {esc(item["id"])}"></a>'
                    )
                publication = f'<span class="mi-board-published-date">{esc(published_date)}</span>' if published_date else ""
                citation = (
                    f'<div class="mi-board-meta"><a class="mi-board-cite" href="{esc(item["source_url"])}" target="_blank" rel="noopener" '
                    f'title="{esc(item["source_url"])}">{esc(item["id"])} · {esc(item["source_name"])} ↗</a>{publication}</div>'
                    if item.get("source_name") and item.get("source_url") else esc(item["id"])
                )
                card_class = "mi-board-news-card mi-board-news-card--with-image" if inline_image else "mi-board-news-card"
                news_cards.append(
                    f'<article class="{card_class}">'
                    f'<h4 title="Tiêu đề bài báo: {esc(item["title"])}">{esc(editorial_subtitle)}</h4>'
                    f'<div class="mi-board-signal-connection"><strong>Liên hệ {esc(signal_id)}:</strong>'
                    f'<span>{esc(signal_connection)}</span></div>'
                    f'<p>{highlighted_summary}</p>{inline_image}{citation}</article>'
                )

            ot_ids = []
            ot_cards = []
            for heading, fields in ot_records:
                ot_id, kind = record_heading(heading)
                ot_ids.append(ot_id)
                priority = clean_atom(field_text(fields, "Mức độ quan trọng"))
                related = extract_ids(field_text(fields, "Signal liên quan"), "SIGNAL")
                if related != [signal_id]:
                    raise ValueError(f"Broken O/T lineage for {ot_id}: expected {signal_id}, found {related}")
                tone = "threat" if norm(kind) == "threat" else "opportunity"
                ot_cards.append(
                    f'<article class="mi-board-ot mi-board-ot--{tone}">'
                    f'<strong>{esc(ot_id)} {esc(kind)} · {esc(priority)}</strong>'
                    f'<p>{esc(finding_board_copy(field_text(fields, "Nội dung")))}</p></article>'
                )

            map_heading, map_fields = map_records[0]
            pm_id, pm_title = record_heading(map_heading)
            pm_title = finding_board_copy(pm_title)
            mapped_ots = extract_ids(field_text(map_fields, "O/T liên quan"), "OT")
            if mapped_ots != ot_ids:
                raise ValueError(f"Broken Product Mapping lineage for {pm_id}: expected {ot_ids}, found {mapped_ots}")
            mandatory = [finding_board_copy(value) for value in field_bullets(map_fields, "Năng lực bắt buộc")]

            gap_heading, gap_fields = gap_records[0]
            gap_id, _ = record_heading(gap_heading)
            if extract_ids(field_text(gap_fields, "Product Mapping liên quan"), "PM") != [pm_id]:
                raise ValueError(f"Broken Gap lineage for {gap_id}")
            capability_status = clean_atom(
                field_text(gap_fields, "Trạng thái capability")
                or field_text(gap_fields, "Trạng thái năng lực")
            )
            missing_fields: list[str] = []
            for missing_label in ("Capability còn thiếu", "Năng lực còn thiếu", "Tính năng còn thiếu"):
                missing_value = field_text(gap_fields, missing_label)
                missing_bullets = field_bullets(gap_fields, missing_label)
                if missing_value or missing_bullets:
                    missing_fields = ([missing_value] if missing_value else []) + missing_bullets
                    break
            missing = [
                finding_board_copy(value)
                for value in split_semicolon_items(missing_fields)
            ]

            action_heading, action_fields = action_records[0]
            action_id, priority = record_heading(action_heading)
            if extract_ids(field_text(action_fields, "Product Gap liên quan"), "GAP") != [gap_id]:
                raise ValueError(f"Broken Action lineage for {action_id}")
            response = clean_atom(field_text(action_fields, "Hướng phản hồi")).upper()

            related_images = [
                item for item in news_records
                if item["id"] in self.news_images and item["id"] not in inline_image_ids
            ]
            media_after_ot = False
            if signal_id == "SIGNAL-002" and not related_images:
                reused_image = next((item for item in news_records if item["id"] in self.news_images), None)
                if reused_image is not None:
                    related_images = [reused_image]
                    media_after_ot = True
            media_items = []
            for media_index, item in enumerate(related_images, 1):
                news_image = self.news_images[item["id"]]
                self.embedded_news_images.add(item["id"])
                media_items.append(
                    f'<a class="mi-board-media mi-board-media--{news_image["layout"]} mi-board-media--{("primary" if media_index == 1 else "secondary")}" '
                    f'href="{esc(item.get("source_url", ""))}" target="_blank" rel="noopener" '
                    f'title="{esc(item.get("source_url", ""))}">'
                    f'<img src="{news_image["uri"]}" width="{news_image["width"]}" height="{news_image["height"]}" '
                    f'alt="Ảnh nguồn cho {esc(item["id"])}"></a>'
                )
            media = (
                f'<div class="mi-board-media-gallery mi-board-media-gallery--{len(media_items)}">{"".join(media_items)}</div>'
                if media_items else ""
            )
            ot_stack = f'<div class="mi-board-ot-stack">{"".join(ot_cards)}</div>'
            side_content = f"{ot_stack}{media}" if media_after_ot else f"{media}{ot_stack}"
            side_class = "mi-board-side"
            if not media:
                side_class += " mi-board-side--without-media"
            elif media_after_ot:
                side_class += " mi-board-side--media-after"
            title_parts = title.split(",", 1)
            trend_title = (
                f'{esc(title_parts[0].strip())}<br><span>{esc(title_parts[1].strip())}</span>'
                if len(title_parts) == 2 else esc(title)
            )
            page_a = f"""
              <h3 class="mi-board-trend-title">{trend_title}</h3>
              <article class="mi-board-signal"><strong>SIGNAL</strong><p>{keep_phrase_groups(signal)}</p></article>
              <div class="mi-board-a-grid">
                <section class="mi-board-evidence"><h3>EVIDENCE</h3>
                  <div class="mi-board-news-grid mi-board-news-grid--{len(news_cards)}">{"".join(news_cards)}</div>
                </section>
                <aside class="{side_class}">{side_content}</aside>
              </div>
            """
            self.add_standard(
                f"{index:02d} · FINDING {index:02d}A · XU HƯỚNG TRẢI NGHIỆM",
                f"{signal_id} — XU HƯỚNG TRẢI NGHIỆM",
                "",
                page_a,
                "mi-board-slide mi-board-page-a",
            )

            reference_page = f"""
              <article class="mi-technology-template" data-ppt-group="technology-{esc(signal_id.lower())}">
                <span class="mi-fill-placeholder" data-ppt-placeholder="technology-{esc(signal_id.lower())}-content" data-ppt-placeholder-prompt="Team QLSP tự do bổ sung nội dung giải pháp công nghệ cho {esc(signal_id)}" aria-label="Team QLSP tự do bổ sung nội dung giải pháp công nghệ cho {esc(signal_id)}"></span>
              </article>
            """
            self.add_standard(
                f"{index:02d} · FINDING {index:02d}B · GIẢI PHÁP CÔNG NGHỆ",
                f"{signal_id} — GIẢI PHÁP CÔNG NGHỆ",
                "",
                reference_page,
                "mi-board-slide mi-board-reference",
            )

            gap_lines = "".join(
                f'<div class="mi-gap-reference-line"><p>— {esc(item)}</p>'
                f'<div class="mi-gap-reference-blank"><span aria-hidden="true">—</span>'
                f'<span class="mi-fill-placeholder" data-ppt-placeholder="gap-reference-{esc(gap_id.lower())}-{row_index:02d}" '
                f'data-ppt-placeholder-prompt="Team QLSP điền tham chiếu cho tính năng còn thiếu" '
                f'aria-label="Team QLSP điền tham chiếu cho tính năng còn thiếu"></span></div></div>'
                for row_index, item in enumerate(missing, 1)
            )
            page_b = f"""
              <div class="mi-board-market-grid">
                <article class="mi-board-card mi-board-map">
                  <div class="mi-board-card-head"><h3>NHU CẦU THỊ TRƯỜNG</h3></div>
                  <h4>{esc(pm_title)}</h4>
                  <section class="mi-board-field"><strong>Vấn đề thị trường</strong><p>{esc(finding_board_copy(field_text(map_fields, 'Vấn đề thị trường')))}</p></section>
                  <section class="mi-board-field"><strong>Khách hàng mục tiêu</strong><p>{esc(finding_board_copy(field_text(map_fields, 'Khách hàng mục tiêu')))}</p></section>
                </article>
                <article class="mi-board-card mi-board-gap">
                  <div class="mi-board-card-head"><h3>KHOẢNG TRỐNG SẢN PHẨM</h3></div>
                  <div class="mi-gap-reference-head"><strong>TÍNH NĂNG CÒN THIẾU</strong><strong>THAM CHIẾU</strong></div>
                  <div class="mi-gap-reference-list" data-ppt-group="gap-reference-{esc(gap_id.lower())}">{gap_lines}</div>
                </article>
              </div>
              <article class="mi-board-action">
                <div class="mi-board-action-grid">
                  <section><strong>Đề xuất</strong><p>{esc(finding_board_copy(field_text(action_fields, 'Hành động đề xuất')))}</p></section>
                  <section><strong>Bước tiếp theo</strong><p>{esc(finding_board_copy(field_text(action_fields, 'Bước tiếp theo')))}</p></section>
                  <section><strong>Kết quả mong đợi</strong><p>{esc(finding_board_copy(field_text(action_fields, 'Kết quả mong đợi')))}</p></section>
                </div>
              </article>
            """
            self.add_standard(
                f"{index:02d} · FINDING {index:02d}C · ĐỀ XUẤT HÀNH ĐỘNG",
                f"{signal_id} — ĐỀ XUẤT HÀNH ĐỘNG",
                title,
                page_b,
                "mi-board-slide mi-board-page-b mi-board-page-c",
            )

    def build_approach(self):
        section = section_by_name(self.report, "Approach")
        flow_block = next((block for block in section.blocks if norm(block.heading) == norm("Từ Signal đến Action")), None)
        response_block = next((block for block in section.blocks if norm(block.heading) == norm("Cách đọc hướng phản hồi")), None)
        if flow_block is None or response_block is None:
            raise ValueError("Approach must include flow and response-enum explanations")
        flow_cards = "".join(
            f'<article class="mi-approach-step"><span>{index:02d}</span><h4>{esc(entry["label"])}</h4><p>{esc(entry["value"])}</p></article>'
            for index, entry in enumerate(parse_fields(flow_block.lines), 1)
        )
        response_cards = []
        for entry in parse_fields(response_block.lines):
            response = clean_inline(str(entry["label"])).upper()
            style = "deep" if response == "VALIDATE" else "neutral" if response == "MONITOR" else "red"
            response_cards.append(f'<article class="mi-response-card">{badge(response, style)}<p>{esc(entry["value"])}</p></article>')
        required = {"PREPARE", "VALIDATE", "MONITOR", "ACT"}
        found = {clean_inline(str(entry["label"])).upper() for entry in parse_fields(response_block.lines)}
        if found != required:
            raise ValueError(f"Approach response definitions must be exactly {sorted(required)}")
        body = f"""
          <div class="mi-approach-layout">
            <section class="mi-approach-column"><h3>Phương pháp luận</h3><div class="mi-approach-flow">{flow_cards}</div></section>
            <section class="mi-approach-column"><h3>Cách đọc hướng phản hồi</h3><div class="mi-response-grid">{"".join(response_cards)}</div></section>
          </div>"""
        self.add_standard("03 • APPROACH", "Từ Điểm nhấn thị trường đến Đề xuất hành động", "", body, "mi-approach")

    def build_summary(self):
        takeaways = summary_bullets(section_by_name(self.report, "Summary")) or ["Không có nội dung Summary trong báo cáo nguồn."]
        cards = "".join(
            f"""
            <article class="mi-summary-card">
              {badge(f'{index:02d}')}
              <p>{esc(takeaway)}</p>
            </article>
            """ for index, takeaway in enumerate(takeaways, 1)
        )
        self.add_standard(
            "07 • SUMMARY",
            "Điểm chốt điều hành",
            "Tóm tắt nguyên văn theo nội dung đã được duyệt",
            f'<div class="mi-grid mi-grid--2 mi-summary-grid">{cards}</div>',
            "mi-summary",
        )

    def build(self) -> str:
        self.build_cover_from_overlay()
        self.build_executive_summary()
        self.build_findings_board()
        self.build_approach()
        total = len(self.slides)
        slide_markup = []
        for index, slide in enumerate(self.slides, 1):
            footer = "" if index == 1 else f"""
              <footer class="mi-slide-footer">
                <span class="mi-footer-rule"></span>
                <span>VSF • Market Intelligence • {esc(self.run_id)}</span>
                <span>{index:02d} / {total:02d}</span>
              </footer>
            """
            slide_markup.append(f"""
              <section class="mi-slide {slide.classes}" id="slide-{index}" data-index="{index - 1}" data-ppt-slide aria-label="Slide {index}: {esc(slide.title)}">
                {slide.markup}
                {footer}
              </section>
            """)
        return document_template("".join(slide_markup), total, self.report.title)


def document_template(slides: str, total: int, title: str) -> str:
    heading_font_uri = font_data_uri(HEADING_FONT_PATH)
    body_font_uri = font_data_uri(BODY_FONT_PATH)
    return f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>{esc(title)} • VSF</title>
  <style>
    @font-face {{
      font-family: "VSF Pro";
      src: url("{heading_font_uri}") format("truetype");
      font-style: normal;
      font-weight: 700;
      font-display: block;
    }}
    @font-face {{
      font-family: "Lexend";
      src: url("{body_font_uri}") format("truetype");
      font-style: normal;
      font-weight: 100 900;
      font-display: block;
    }}
    :root {{
      --vsf-red: #ea0a2a;
      --vsf-deep-red: #9f1028;
      --vsf-bg: #f4f4f6;
      --vsf-surface: #ffffff;
      --vsf-soft: #ebebee;
      --vsf-text: #171719;
      --vsf-muted: #66666b;
      --vsf-border: #dddde2;
      --vsf-shadow: 0 18px 55px rgba(18, 18, 22, .10);
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; background: #d8d8dc; }}
    body {{ margin: 0; color: var(--vsf-text); background: #d8d8dc; font-family: "Lexend", "Segoe UI", Arial, sans-serif; }}
    button {{ font: inherit; }}
    .mi-deck {{ height: 100vh; overflow-y: auto; scroll-snap-type: y mandatory; scroll-behavior: smooth; }}
    .mi-slide {{
      position: relative; display: flex; flex-direction: column; width: 100%; min-height: 100vh;
      padding: clamp(30px, 5vh, 58px) clamp(28px, 5vw, 78px) clamp(46px, 6vh, 66px);
      overflow: hidden; scroll-snap-align: start; background: var(--vsf-bg);
    }}
    .mi-slide::before {{ content: ""; position: absolute; inset: 0 0 auto; height: 9px; background: var(--vsf-red); }}
    .mi-slide-header {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: start; gap: 28px; min-height: 118px; }}
    .mi-header-copy {{ min-width: 0; }}
    .mi-eyebrow {{ margin: 0 0 16px; color: var(--vsf-red); font-size: 13px; font-weight: 800; letter-spacing: .04em; }}
    h1, h2, h3, p {{ overflow-wrap: anywhere; }}
    h1, h2, h3, h4 {{ margin-top: 0; font-family: "VSF Pro", "Lexend", "Segoe UI", Arial, sans-serif; }}
    .mi-slide h2 {{ margin-bottom: 8px; font-size: clamp(32px, 3.2vw, 49px); line-height: 1.04; letter-spacing: -.025em; }}
    .mi-subtitle {{ margin: 0; color: var(--vsf-muted); font-size: clamp(15px, 1.2vw, 19px); }}
    .mi-logo {{ display: grid; place-items: center; width: clamp(150px, 13vw, 205px); min-height: 66px; padding: 0; background: transparent; }}
    .mi-logo img {{ display: block; width: 100%; height: auto; }}
    .mi-slide-body {{ flex: 1; min-height: 0; padding-top: clamp(18px, 2.3vh, 30px); }}
    .mi-grid {{ display: grid; gap: clamp(14px, 1.6vw, 24px); height: 100%; min-height: 0; }}
    .mi-grid--1 {{ grid-template-columns: minmax(0, 760px); justify-content: center; }}
    .mi-grid--2 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .mi-grid--3 {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    .mi-grid--4 {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
    .mi-panel, .mi-news-card, .mi-signal-card, .mi-ot-card, .mi-stat-card, .mi-summary-card, .mi-agenda-item {{
      border: 1px solid var(--vsf-border); border-radius: 28px; background: var(--vsf-surface); box-shadow: var(--vsf-shadow);
    }}
    .mi-badge {{ display: inline-flex; align-items: center; justify-content: center; min-height: 34px; padding: 6px 16px; border-radius: 7px; font-size: 12px; font-weight: 800; letter-spacing: .015em; white-space: nowrap; }}
    .mi-badge--red {{ color: #fff; background: var(--vsf-red); }}
    .mi-badge--deep {{ color: #fff; background: var(--vsf-deep-red); }}
    .mi-badge--neutral {{ color: var(--vsf-text); background: var(--vsf-soft); }}
    .mi-badge--outline {{ color: var(--vsf-red); border: 1px solid var(--vsf-red); background: #fff; }}
    .mi-mini-rule {{ width: 92px; height: 5px; margin: 18px 0; background: var(--vsf-red); box-shadow: 0 3px 5px rgba(0,0,0,.15); }}
    .mi-slide-footer {{ position: absolute; inset: auto clamp(28px, 5vw, 78px) 22px; display: grid; grid-template-columns: 30px 1fr auto; align-items: center; gap: 12px; color: var(--vsf-muted); font-size: 11px; }}
    .mi-footer-rule {{ height: 4px; background: var(--vsf-red); }}
    .mi-cover {{ display: grid; grid-template-columns: minmax(0, 1fr); align-items: center; padding-left: clamp(54px, 6vw, 92px); padding-right: clamp(42px, 5vw, 78px); }}
    .mi-cover-background {{ position: absolute; z-index: 0; inset: 0; overflow: hidden; pointer-events: none; }}
    .mi-cover-background img {{ display: block; width: 100%; height: 100%; object-fit: cover; object-position: center center; }}
    .mi-cover-copy, .mi-cover-brand {{ position: relative; z-index: 1; }}
    .mi-cover::after {{ content: ""; position: absolute; inset: 0 auto 0 0; width: 24px; background: var(--vsf-red); box-shadow: 6px 0 0 var(--vsf-deep-red); }}
    .mi-cover-copy h1 {{ max-width: 900px; margin: 0; font-size: clamp(48px, 5.3vw, 84px); line-height: 1.02; letter-spacing: -.04em; }}
    .mi-cover-subtitle {{ margin: clamp(26px, 4vh, 48px) 0 0; color: var(--vsf-muted); font-size: clamp(20px, 2vw, 31px); }}
    .mi-cover-subtitle-line2 {{ display: inline-block; margin-top: 4px; color: var(--vsf-red); }}
    .mi-cover-rule {{ width: 132px; height: 7px; margin: clamp(28px, 4vh, 48px) 0 26px; background: var(--vsf-red); }}
    .mi-cover-date {{ margin: 0; color: var(--vsf-text); font-size: clamp(18px, 1.55vw, 24px); font-weight: 750; letter-spacing: .01em; }}
    .mi-cover-brand {{ position: absolute; top: clamp(32px, 4.2vh, 48px); right: clamp(34px, 4vw, 58px); }}
    .mi-cover-brand .mi-logo {{ width: 136px; min-height: 60px; }}
    .mi-cover-flow {{ padding: clamp(24px, 3vw, 44px); border-radius: 48px; color: #fff; background: var(--vsf-red); box-shadow: var(--vsf-shadow); }}
    .mi-cover-flow > p {{ margin: 0 0 20px; text-align: center; font-weight: 800; }}
    .mi-cover-flow ol {{ display: grid; gap: 12px; margin: 0; padding: 0; list-style: none; }}
    .mi-cover-flow--stages-only {{ display: flex; align-items: center; }}
    .mi-cover-flow--stages-only ol {{ width: 100%; }}
    .mi-cover-flow li {{ padding: 12px 16px; border-radius: 10px; color: var(--vsf-deep-red); background: #fff; text-align: center; font-weight: 800; box-shadow: 0 6px 10px rgba(75,0,15,.18); }}
    .mi-cover-flow .mi-logo {{ width: 100%; }}
    .mi-agenda-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 15px 24px; }}
    .mi-agenda-item {{ display: grid; grid-template-columns: auto 1fr; align-items: center; gap: 18px; min-height: 78px; padding: 14px 18px; border-radius: 18px; }}
    .mi-agenda-item h3 {{ margin: 0 0 4px; font-size: 18px; }}
    .mi-agenda-item p {{ margin: 0; color: var(--vsf-muted); }}
    .mi-provenance {{ max-width: 600px; margin: 20px 0 0 auto; font-size: 17px; font-weight: 700; }}
    .mi-stat-card {{ padding: clamp(20px, 2vw, 30px); }}
    .mi-stat-card > strong {{ color: var(--vsf-red); font-family: "VSF Pro", "Lexend", sans-serif; font-size: clamp(38px, 4vw, 58px); }}
    .mi-stat-card h3 {{ margin: 14px 0; font-size: clamp(18px, 1.5vw, 24px); }}
    .mi-stat-card p {{ color: var(--vsf-muted); font-size: 13px; line-height: 1.8; }}
    .mi-news-card, .mi-signal-card {{ display: flex; flex-direction: column; min-height: 0; padding: clamp(20px, 2vw, 30px); }}
    .mi-news-card h3, .mi-signal-card h3 {{ margin: 22px 0 0; font-size: clamp(20px, 1.75vw, 28px); line-height: 1.17; }}
    .mi-news-card > p, .mi-body-copy {{ margin: 0; color: var(--vsf-muted); font-size: clamp(14px, 1.15vw, 18px); line-height: 1.42; }}
    .mi-lineage {{ margin-top: auto; padding-top: 20px; }}
    .mi-lineage span, .mi-panel h3, .mi-facts span, .mi-action-hero h3 {{ display: block; margin: 0 0 10px; color: var(--vsf-red); font-size: 12px; font-weight: 800; letter-spacing: .025em; }}
    .mi-lineage strong {{ font-size: 13px; }}
    .mi-grid--ot {{ grid-template-rows: repeat(2, minmax(0, 1fr)); }}
    .mi-ot-card {{ display: flex; flex-direction: column; min-height: 0; padding: clamp(16px, 1.5vw, 24px); }}
    .mi-badge-row {{ display: grid; grid-template-columns: auto auto 1fr; align-items: center; gap: 12px; }}
    .mi-badge-row .mi-badge:last-child {{ justify-self: end; }}
    .mi-ot-card > p {{ margin: 18px 0 10px; font-size: clamp(14px, 1.05vw, 17px); line-height: 1.35; }}
    .mi-lineage--inline {{ display: flex; align-items: baseline; gap: 9px; padding-top: 10px; }}
    .mi-lineage--inline span {{ color: var(--vsf-muted); }}
    .mi-record-tag {{ margin-bottom: 16px; }}
    .mi-mapping-layout, .mi-gap-layout {{ display: grid; grid-template-columns: minmax(0, 2fr) minmax(260px, .95fr); gap: 24px; min-height: 0; height: calc(100% - 50px); }}
    .mi-stack {{ display: grid; grid-template-rows: auto 1fr; gap: 18px; min-height: 0; }}
    .mi-panel {{ min-height: 0; padding: clamp(20px, 2vw, 30px); }}
    .mi-panel--soft {{ background: var(--vsf-soft); }}
    .mi-panel p {{ margin: 0; font-size: clamp(15px, 1.25vw, 19px); line-height: 1.43; }}
    .mi-panel--compact p {{ font-size: clamp(15px, 1.35vw, 21px); }}
    .mi-list {{ display: grid; gap: 10px; margin: 0; padding-left: 22px; font-size: clamp(14px, 1.15vw, 18px); line-height: 1.34; }}
    .mi-facts {{ display: grid; align-content: start; gap: clamp(18px, 2.5vh, 30px); }}
    .mi-facts strong {{ font-size: clamp(18px, 1.8vw, 28px); }}
    .mi-facts p {{ font-size: clamp(14px, 1.05vw, 17px); }}
    .mi-action-hero {{ padding: clamp(22px, 2.2vw, 34px); border-radius: 28px; color: #fff; background: var(--vsf-red); box-shadow: var(--vsf-shadow); }}
    .mi-action-hero h3 {{ color: #fff; }}
    .mi-action-hero p {{ margin: 0; font-family: "VSF Pro", "Lexend", sans-serif; font-size: clamp(20px, 2vw, 30px); font-weight: 700; line-height: 1.25; }}
    .mi-action-grid {{ display: grid; grid-template-columns: 1.8fr .86fr .96fr; gap: 22px; margin-top: 24px; }}
    .mi-action-grid .mi-panel {{ min-height: clamp(190px, 31vh, 290px); }}
    .mi-summary-grid {{ grid-template-rows: repeat(2, minmax(0, 1fr)); }}
    .mi-summary-card {{ display: grid; grid-template-columns: auto 1fr; align-items: start; gap: 20px; padding: clamp(20px, 2vw, 30px); }}
    .mi-summary-card p {{ margin: 0; font-size: clamp(16px, 1.4vw, 22px); font-weight: 750; line-height: 1.38; }}
    .mi-signal-lineage {{ padding-top: clamp(22px, 3vh, 34px); }}
    .mi-signal-lineage .mi-slide-header {{ min-height: 76px; }}
    .mi-signal-lineage .mi-eyebrow {{ margin-bottom: 8px; }}
    .mi-signal-lineage h2 {{ font-size: clamp(28px, 2.65vw, 42px); }}
    .mi-signal-lineage .mi-subtitle {{ font-size: clamp(14px, 1vw, 16px); line-height: 1.2; }}
    .mi-signal-lineage .mi-logo {{ width: clamp(132px, 10vw, 162px); min-height: 54px; }}
    .mi-signal-lineage .mi-slide-body {{ padding-top: 8px; }}
    .mi-product-slide .mi-slide-header {{ min-height: 92px; }}
    .mi-product-slide .mi-slide-body {{ padding-top: 12px; }}
    .mi-signal-lineage-layout {{ display: grid; grid-template-columns: minmax(0, 2.15fr) minmax(280px, .85fr); gap: 18px; height: 100%; min-height: 0; }}
    .mi-signal-evidence {{ display: grid; grid-template-rows: auto 24px minmax(0, 1fr); gap: 8px; min-height: 0; }}
    .mi-signal-hero, .mi-lineage-news, .mi-lineage-ot, .mi-product-col, .mi-product-action {{ border: 1px solid var(--vsf-border); border-radius: 16px; background: #fff; padding: 14px; }}
    .mi-signal-hero {{ border-color: #8bb8ff; background: #f5f9ff; }}
    .mi-signal-hero h3, .mi-column-title, .mi-product-col > h3 {{ margin: 0 0 7px; color: var(--vsf-red); }}
    .mi-signal-hero p, .mi-lineage-news p, .mi-lineage-ot p, .mi-product-col p {{ margin: 7px 0 0; line-height: 1.32; }}
    .mi-column-title {{ font-size: 18px; }}
    .mi-news-strip {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); align-items: stretch; gap: 10px; min-height: 0; height: 100%; }}
    .mi-lineage-news {{ display: flex; flex-direction: column; min-height: 0; overflow: visible; padding: 16px; }}
    .mi-lineage-news h4 {{ margin: 8px 0 0; font-size: 13px; line-height: 1.22; }}
    .mi-lineage-news p {{ display: block; margin-top: 8px; overflow: visible; font-size: clamp(10.5px, .78vw, 12px); line-height: 1.25; }}
    .mi-news-cite {{ align-self: flex-start; margin-top: auto; padding-top: 7px; color: var(--vsf-deep-red); font-size: 9.5px; font-weight: 750; line-height: 1.15; text-decoration: none; white-space: nowrap; }}
    .mi-news-cite:hover, .mi-news-cite:focus-visible {{ text-decoration: underline; }}
    .mi-ot-stack {{ border-left: 1px solid var(--vsf-border); padding-left: 18px; overflow: visible; }}
    .mi-lineage-ot {{ position: relative; margin-bottom: 10px; overflow: visible; font-size: 13px; }}
    .mi-lineage-ot .mi-badge-row {{ position: relative; z-index: 2; width: max-content; max-width: none; grid-template-columns: max-content max-content max-content; }}
    .mi-lineage-ot--threat {{ border-color: #ef9b9b; background: #fff8f8; }}
    .mi-lineage-ot--opportunity {{ border-color: #94c99d; background: #f7fcf7; }}
    .mi-action-guide-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); align-items: stretch; gap: 18px; height: 100%; min-height: 0; }}
    .mi-action-guide-card {{ border: 1px solid var(--vsf-border); border-radius: 22px; background: #fff; padding: clamp(20px, 2vw, 30px); box-shadow: var(--vsf-shadow); }}
    .mi-action-guide-card--prepare {{ border-color: #ef9999; background: #fffafa; }}
    .mi-action-guide-card--validate {{ border-color: #bd8e9a; background: #fff9fb; }}
    .mi-action-guide-card--monitor {{ border-color: #b9b9c0; background: #fafafa; }}
    .mi-action-guide-card--act {{ border-color: #73a6ed; background: #f8fbff; }}
    .mi-action-guide-card .mi-badge-row {{ display: flex; flex-wrap: wrap; justify-content: flex-start; }}
    .mi-action-guide-card p {{ margin: 22px 0 0; font-size: clamp(15px, 1.15vw, 18px); line-height: 1.42; }}
    .mi-product-triad {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; height: 100%; min-height: 0; }}
    .mi-product-col {{ overflow: hidden; font-size: 13px; line-height: 1.3; }}
    .mi-product-map {{ border-color: #73a6ed; background: #f8fbff; }}
    .mi-product-gap {{ border-color: #87bf8a; background: #f8fcf8; }}
    .mi-product-actions {{ border-color: #ef9999; background: #fffafa; }}
    .mi-product-action .mi-badge-row {{ display: flex; flex-wrap: wrap; justify-content: flex-start; }}
    .mi-product-map > h3 {{ color: #1761c4; }} .mi-product-gap > h3 {{ color: #278232; }} .mi-product-actions > h3 {{ color: #d50b1f; }}
    .mi-product-action {{ margin-top: 8px; padding: 10px; border-color: #f0b0b0; }}
    .mi-product-action p {{ font-size: 12px; margin-top: 6px; }}
    .mi-missing-capabilities {{ margin-top: 8px; }}
    .mi-missing-capabilities > strong {{ display: block; margin-bottom: 6px; }}
    .mi-missing-list {{ display: grid; gap: 5px; margin: 0; padding: 0; list-style: none; font-size: 12px; line-height: 1.22; }}
    .mi-missing-list li {{ display: grid; grid-template-columns: 10px minmax(0, 1fr); gap: 3px; }}
    .mi-missing-list li::before {{ content: "-"; font-weight: 800; }}
    .mi-executive-summary .mi-slide-header {{ min-height: 88px; }}
    .mi-executive-summary .mi-slide-body {{ padding-top: 10px; }}
    .mi-exec-list {{ display: grid; gap: 10px; height: 100%; }}
    .mi-exec-row {{ display: grid; grid-template-columns: minmax(0, 1.34fr) minmax(180px, .62fr) 28px minmax(0, 1.18fr); align-items: stretch; gap: 10px; min-height: 0; }}
    .mi-exec-signal, .mi-exec-action {{ display: grid; min-width: 0; grid-template-columns: minmax(112px, auto) 1fr; align-items: center; gap: 14px; padding: 11px 14px; border: 1px solid var(--vsf-border); border-radius: 14px; background: #fff; }}
    .mi-exec-technology {{ display: flex; min-width: 0; flex-direction: column; gap: 8px; padding: 11px 13px; border: 1px solid var(--vsf-border); border-radius: 14px; background: #fff; }}
    .mi-exec-technology > strong {{ color: #555; font-size: 11px; font-style: italic; font-weight: 500; }}
    .mi-exec-technology-placeholder {{ flex: 1 1 auto; min-height: 62px; border: 1px dashed #c9c9c7; border-radius: 6px; background: #fbfbfa; }}
    .mi-exec-action {{ grid-template-columns: minmax(0, 1fr); align-content: center; border-color: #ef9999; background: #fffafa; }}
    .mi-exec-signal p, .mi-exec-action p {{ margin: 0; font-size: clamp(13px, 1vw, 16px); font-weight: 400; line-height: 1.25; }}
    .mi-exec-emphasis {{ color: #171719; font-weight: 800; }}
    .mi-exec-action .mi-badge-row {{ display: flex; min-width: 0; flex-wrap: wrap; justify-content: flex-start; }}
    .mi-fill-placeholder {{ display: block; min-width: 0; min-height: 16px; }}
    .mi-exec-verified {{ display: grid; grid-template-columns: auto auto minmax(0, 1fr); align-items: center; gap: 7px; color: #767676; font-size: 10.5px; }}
    .mi-exec-verified strong {{ white-space: nowrap; }}
    .mi-waiting-badge {{ padding: 3px 6px; border: 1px solid #efc36b; border-radius: 999px; background: #fff6dc; color: #805600; font-size: 8.4px; font-weight: 800; letter-spacing: .035em; white-space: nowrap; }}
    .mi-exec-verified-placeholder {{ min-height: 15px; border-bottom: 1px dashed #c5c5c5; }}
    .mi-exec-arrow {{ display: grid; place-items: center; color: var(--vsf-red); font-size: 24px; font-weight: 900; }}
    .mi-finding {{ padding-top: clamp(18px, 2.2vh, 28px); }}
    .mi-finding .mi-slide-header {{ min-height: 70px; }}
    .mi-finding .mi-eyebrow {{ margin-bottom: 6px; }}
    .mi-finding h2 {{ font-size: clamp(25px, 2.25vw, 36px); }}
    .mi-finding .mi-subtitle {{ font-size: 13px; }}
    .mi-finding .mi-logo {{ width: clamp(120px, 9vw, 150px); min-height: 48px; }}
    .mi-finding .mi-slide-body {{ display: grid; grid-template-rows: auto minmax(0, 1fr) minmax(0, 1.06fr); gap: 9px; padding-top: 7px; }}
    .mi-finding-signal {{ display: grid; grid-template-columns: auto 1fr; align-items: center; gap: 14px; padding: 9px 14px; border: 1px solid #8bb8ff; border-radius: 13px; background: #f5f9ff; }}
    .mi-finding-signal span {{ color: #1761c4; font-size: 11px; font-weight: 850; letter-spacing: .05em; }}
    .mi-finding-signal p {{ margin: 0; font-size: clamp(13px, 1vw, 16px); font-weight: 700; line-height: 1.25; }}
    .mi-finding-evidence {{ display: grid; grid-template-columns: minmax(0, 2.1fr) minmax(260px, .9fr); gap: 10px; min-height: 0; }}
    .mi-finding-evidence > section {{ display: flex; flex-direction: column; min-height: 0; }}
    .mi-finding-evidence h3 {{ margin: 0 0 5px; color: var(--vsf-red); font-size: 13px; }}
    .mi-finding-news-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 7px; min-height: 0; height: 100%; }}
    .mi-finding-news-grid--1 {{ grid-template-columns: 1fr; }}
    .mi-finding-news-grid--2 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .mi-finding-news {{ display: grid; min-height: 0; overflow: hidden; border: 1px solid var(--vsf-border); border-radius: 12px; background: #fff; }}
    .mi-finding-news--image-top {{ grid-template-columns: 1fr; grid-template-rows: clamp(120px, 18vh, 190px) minmax(0, 1fr); }}
    .mi-finding-news--image-side {{ grid-template-columns: minmax(120px, .82fr) minmax(0, 1.18fr); grid-template-rows: 1fr; }}
    .mi-finding-news-copy {{ display: flex; flex-direction: column; min-width: 0; padding: 9px; }}
    .mi-finding-news h4 {{ margin: 6px 0 0; font-size: 11.5px; line-height: 1.18; }}
    .mi-finding-news p {{ margin: 5px 0 0; color: var(--vsf-muted); font-size: 10.5px; line-height: 1.2; }}
    .mi-news-image {{ display: block; min-height: 0; overflow: hidden; background: var(--vsf-soft); }}
    .mi-news-image img {{ width: 100%; height: 100%; min-height: 100%; object-fit: cover; }}
    .mi-finding-news--image-side .mi-news-image {{ display: grid; place-items: center; padding: 14px; background: #f1f2f4; }}
    .mi-finding-news--image-side .mi-news-image img {{ width: 100%; height: 100%; min-height: 0; object-fit: contain; object-position: center; }}
    .mi-finding-news--image-top .mi-news-image img {{ object-fit: cover; object-position: center; }}
    .mi-finding-news .mi-news-cite {{ margin-top: auto; padding-top: 4px; font-size: 8.7px; }}
    .mi-finding-ot-stack {{ display: grid; gap: 7px; min-height: 0; height: 100%; }}
    .mi-finding-ot {{ padding: 9px; border: 1px solid var(--vsf-border); border-radius: 12px; background: #fff; }}
    .mi-finding-ot--opportunity {{ border-color: #94c99d; background: #f7fcf7; }}
    .mi-finding-ot--threat {{ border-color: #ef9b9b; background: #fff8f8; }}
    .mi-finding-ot .mi-badge-row {{ display: flex; flex-wrap: wrap; justify-content: flex-start; gap: 5px; }}
    .mi-finding-ot .mi-badge {{ min-height: 24px; padding: 3px 8px; font-size: 9px; }}
    .mi-finding-ot p {{ margin: 6px 0 0; font-size: 10.5px; line-height: 1.2; }}
    .mi-finding-decision {{ display: grid; grid-template-columns: minmax(0, .9fr) minmax(0, .9fr) minmax(0, 1.2fr); gap: 8px; min-height: 0; }}
    .mi-finding-news-slide .mi-slide-body {{ display: grid; grid-template-rows: auto minmax(0, 1fr); gap: 14px; padding-top: 10px; }}
    .mi-finding-news-slide .mi-finding-signal {{ padding: 14px 18px; }}
    .mi-finding-news-slide .mi-finding-signal span {{ font-size: 13px; }}
    .mi-finding-news-slide .mi-finding-signal p {{ font-size: clamp(17px, 1.35vw, 22px); line-height: 1.3; }}
    .mi-news-section {{ display: flex; flex-direction: column; min-height: 0; }}
    .mi-news-section > h3 {{ margin: 0 0 8px; color: var(--vsf-red); font-size: 17px; }}
    .mi-finding-news-slide .mi-finding-news-grid {{ flex: 1; gap: 12px; }}
    .mi-finding-news-grid--4 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); grid-template-rows: repeat(2, minmax(0, 1fr)); }}
    .mi-finding-news-slide .mi-finding-news-copy {{ padding: 13px; }}
    .mi-finding-news-slide .mi-finding-news h4 {{ margin-top: 8px; font-size: clamp(14px, 1.05vw, 17px); line-height: 1.22; }}
    .mi-finding-news-slide .mi-finding-news p {{ margin-top: 7px; font-size: clamp(13px, .92vw, 15px); line-height: 1.3; }}
    .mi-finding-news-slide .mi-finding-news .mi-news-cite {{ font-size: 10px; padding-top: 7px; }}
    .mi-finding-decision-slide .mi-slide-body {{ display: block; padding-top: 10px; }}
    .mi-decision-four {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); grid-template-rows: repeat(2, minmax(0, 1fr)); gap: 14px; height: 100%; min-height: 0; }}
    .mi-decision-four > .mi-decision-card, .mi-decision-panel {{ min-height: 0; overflow: hidden; padding: 16px 18px; border: 1px solid var(--vsf-border); border-radius: 15px; background: #fff; }}
    .mi-decision-ot {{ border-color: #ef9999; background: #fffafa; }}
    .mi-panel-title {{ display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 10px; color: var(--vsf-red); font-size: 13px; font-weight: 850; letter-spacing: .04em; }}
    .mi-panel-title small {{ color: var(--vsf-muted); font-size: 10px; }}
    .mi-decision-four .mi-finding-ot-stack {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; height: auto; }}
    .mi-decision-four .mi-finding-ot {{ padding: 11px; }}
    .mi-decision-four .mi-finding-ot p {{ font-size: 13px; line-height: 1.3; }}
    .mi-decision-four .mi-decision-head {{ margin-bottom: 10px; }}
    .mi-decision-four .mi-decision-head > span:first-child {{ font-size: 13px; }}
    .mi-decision-four .mi-decision-card .mi-badge {{ min-height: 27px; padding: 4px 10px; font-size: 10px; }}
    .mi-decision-four .mi-decision-card h4 {{ margin-bottom: 8px; font-size: 16px; line-height: 1.24; }}
    .mi-decision-four .mi-decision-card p, .mi-decision-four .mi-gap-missing {{ margin-top: 7px; font-size: 13px; line-height: 1.3; }}
    .mi-decision-four .mi-gap-missing-list {{ gap: 3px; }}
    .mi-decision-card {{ min-height: 0; overflow: hidden; padding: 10px; border: 1px solid var(--vsf-border); border-radius: 12px; background: #fff; }}
    .mi-decision-map {{ border-color: #73a6ed; background: #f8fbff; }}
    .mi-decision-gap {{ border-color: #87bf8a; background: #f8fcf8; }}
    .mi-decision-action {{ border-color: #ef9999; background: #fffafa; }}
    .mi-decision-head {{ display: flex; align-items: center; justify-content: space-between; gap: 6px; margin-bottom: 6px; }}
    .mi-decision-head > span:first-child {{ color: var(--vsf-red); font-size: 10px; font-weight: 850; letter-spacing: .05em; }}
    .mi-decision-head > div {{ display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 4px; }}
    .mi-decision-card .mi-badge {{ min-height: 23px; padding: 3px 7px; font-size: 8.8px; }}
    .mi-decision-card .mi-badge-row {{ display: flex; flex-wrap: wrap; justify-content: flex-start; gap: 4px; margin-bottom: 5px; }}
    .mi-decision-card h4 {{ margin: 0 0 5px; font-size: 11.5px; line-height: 1.18; }}
    .mi-decision-card p {{ margin: 4px 0 0; font-size: 9.8px; line-height: 1.17; }}
    .mi-gap-missing {{ margin-top: 5px; font-size: 9.8px; line-height: 1.17; }}
    .mi-gap-missing > strong {{ display: block; margin-bottom: 3px; }}
    .mi-gap-missing-list {{ display: grid; gap: 2px; margin: 0; padding: 0; list-style: none; }}
    .mi-gap-missing-list li {{ display: grid; grid-template-columns: 8px minmax(0, 1fr); gap: 2px; }}
    .mi-gap-missing-list li::before {{ content: "-"; font-weight: 800; }}
    .mi-approach .mi-slide-header {{ min-height: 86px; }}
    .mi-approach .mi-slide-header {{ grid-template-columns: minmax(0, 1fr) 170px; gap: 18px; }}
    .mi-approach h2 {{ max-width: 100%; font-size: clamp(28px, 2.15vw, 34px); white-space: normal; overflow-wrap: anywhere; line-height: 1.06; }}
    .mi-approach .mi-slide-body {{ padding-top: 10px; }}
    .mi-approach-layout {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; height: 100%; min-height: 0; }}
    .mi-approach-column {{ display: flex; flex-direction: column; min-height: 0; }}
    .mi-approach-layout h3 {{ flex: 0 0 34px; align-self: stretch; margin: 0; color: var(--vsf-red); font-size: 18px; line-height: 1.2; }}
    .mi-approach-flow {{ display: grid; flex: 1 1 auto; grid-template-rows: repeat(5, minmax(0, 1fr)); gap: 7px; min-height: 0; }}
    .mi-approach-step {{ display: grid; grid-template-columns: 36px 170px minmax(0, 1fr); align-items: center; gap: 10px; padding: 10px 12px; border: 1px solid var(--vsf-border); border-radius: 13px; background: #fff; }}
    .mi-approach-step > span {{ color: var(--vsf-red); font-weight: 850; }}
    .mi-approach-step h4, .mi-approach-step p {{ margin: 0; }}
    .mi-approach-step h4 {{ min-width: 0; font-size: 13px; line-height: 1.08; overflow-wrap: anywhere; }}
    .mi-approach-step p {{ color: var(--vsf-muted); font-size: 13.5px; line-height: 1.25; }}
    .mi-response-grid {{ display: grid; flex: 1 1 auto; grid-template-columns: repeat(2, minmax(0, 1fr)); grid-template-rows: repeat(2, minmax(0, 1fr)); gap: 9px; min-height: 0; }}
    .mi-response-card {{ min-height: 0; padding: 14px; border: 1px solid var(--vsf-border); border-radius: 14px; background: #fff; }}
    .mi-response-card p {{ margin: 10px 0 0; font-size: 13.5px; line-height: 1.3; }}
    .mi-controls {{ position: fixed; z-index: 50; right: 22px; bottom: 20px; display: flex; align-items: center; gap: 8px; padding: 8px; border: 1px solid rgba(255,255,255,.35); border-radius: 14px; color: #fff; background: rgba(159,16,40,.96); box-shadow: 0 12px 30px rgba(50,0,12,.28); backdrop-filter: blur(12px); }}
    .mi-controls button {{ display: inline-grid; place-items: center; width: 38px; height: 36px; border: 0; border-radius: 8px; color: #fff; background: transparent; cursor: pointer; font-weight: 800; }}
    .mi-controls button:hover, .mi-controls button:focus-visible {{ background: rgba(255,255,255,.16); outline: 2px solid #fff; outline-offset: 1px; }}
    .mi-controls button:disabled {{ opacity: .35; cursor: default; }}
    .mi-counter {{ min-width: 74px; text-align: center; font-size: 12px; font-variant-numeric: tabular-nums; }}
    .mi-progress {{ position: fixed; z-index: 55; inset: 0 auto auto 0; width: 0; height: 9px; background: var(--vsf-deep-red); transition: width .24s ease; }}
    .sr-only {{ position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }}
    @media (max-width: 1100px) {{
      .mi-grid--4 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .mi-action-guide-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .mi-news-overview .mi-slide-body {{ overflow: auto; }}
      .mi-slide h2 {{ max-width: 820px; }}
    }}
    @media (max-width: 820px) {{
      .mi-deck {{ height: auto; overflow: visible; scroll-snap-type: none; }}
      .mi-slide {{ min-height: 100vh; height: auto; overflow: visible; padding: 28px 20px 72px; }}
      .mi-slide-header {{ grid-template-columns: 1fr; min-height: auto; }}
      .mi-logo {{ width: 150px; order: -1; }}
      .mi-approach h2 {{ white-space: normal; }}
      .mi-grid--2, .mi-grid--3, .mi-grid--4, .mi-agenda-grid, .mi-mapping-layout, .mi-gap-layout, .mi-action-grid {{ grid-template-columns: 1fr; }}
      .mi-action-guide-grid {{ grid-template-columns: 1fr; }}
      .mi-grid--ot, .mi-summary-grid {{ grid-template-rows: none; }}
      .mi-grid {{ height: auto; }}
      .mi-cover {{ display: flex; gap: 24px; padding-left: 44px; padding-right: 24px; flex-wrap: wrap; }}
      .mi-cover-copy {{ flex: 1 1 520px; }}
      .mi-cover-flow {{ width: 100%; max-width: 420px; }}
      .mi-slide-footer {{ inset-inline: 20px; }}
      .mi-action-grid .mi-panel {{ min-height: 0; }}
      .mi-exec-row, .mi-exec-signal, .mi-exec-technology, .mi-exec-action, .mi-finding-evidence, .mi-finding-decision, .mi-approach-layout, .mi-approach-step {{ grid-template-columns: 1fr; }}
      .mi-exec-arrow {{ transform: rotate(90deg); }}
      .mi-finding .mi-slide-body {{ display: block; }}
      .mi-finding-news-grid, .mi-finding-news-grid--2, .mi-finding-news-grid--3, .mi-finding-news-grid--4, .mi-response-grid, .mi-decision-four, .mi-decision-four .mi-finding-ot-stack {{ grid-template-columns: 1fr; }}
      .mi-finding-evidence, .mi-finding-decision {{ margin-top: 14px; }}
    }}
    .mi-board-slide {{
      --board-red: #e5002b; --board-text: #202124; --board-muted: #666; --board-border: #dddcd8;
      --board-signal: #eaf3ff; --board-signal-border: #bed5ef;
      height: 100vh; min-height: 100vh;
      padding: clamp(22px, 3vh, 34px) clamp(34px, 4vw, 58px) clamp(44px, 5vh, 56px);
      color: var(--board-text); background: #fff; outline: 1px solid #bfc0c2; outline-offset: -4px;
    }}
    .mi-board-slide::before {{ display: none; }}
    .mi-board-slide .mi-slide-header {{ grid-template-columns: minmax(0, 1fr) 136px; align-items: center; min-height: 0; margin-bottom: 10px; gap: 12px; }}
    .mi-board-slide .mi-eyebrow {{ margin-bottom: 8px; color: var(--board-red); font-size: 12px; letter-spacing: .09em; }}
    .mi-board-slide h2 {{ max-width: 1120px; margin: 0; font-size: clamp(28px, 2.45vw, 38px); line-height: 1.1; text-wrap: pretty; }}
    .mi-keep {{ white-space: nowrap; }}
    .mi-board-slide .mi-subtitle {{ display: none; }}
    .mi-board-slide .mi-logo {{ width: 136px; min-height: 60px; }}
    .mi-board-slide .mi-slide-body {{ display: grid; min-height: 0; padding-top: 8px; }}
    .mi-board-slide .mi-slide-footer {{ inset-inline: clamp(34px, 4vw, 58px); bottom: 18px; grid-template-columns: 1fr auto; font-size: 10px; }}
    .mi-board-slide .mi-footer-rule {{ display: none; }}
    .mi-board-signal {{ display: grid; grid-template-columns: auto 1fr; align-items: center; gap: 16px; padding: 13px 20px; border: 1px solid var(--board-signal-border); border-radius: 8px; color: #0c477e; background: var(--board-signal); }}
    .mi-board-signal strong {{ color: var(--board-red); font: 800 14px "VSF Pro", "Lexend", sans-serif; }}
    .mi-board-signal p {{ margin: 0; font-size: clamp(15.5px, 1.16vw, 18px); line-height: 1.34; text-wrap: pretty; }}
    .mi-board-page-a .mi-slide-body {{ grid-template-rows: auto auto minmax(0, 1fr); gap: 10px; }}
    .mi-board-trend-title {{ max-width: 1080px; margin: 0; font: 800 clamp(20px, 1.7vw, 26px)/1.08 "VSF Pro", "Lexend", sans-serif; text-transform: uppercase; text-wrap: balance; }}
    .mi-board-trend-title span {{ color: var(--board-red); }}
    .mi-board-a-grid {{ display: grid; grid-template-columns: minmax(0, 1.47fr) minmax(340px, .93fr); gap: 22px; min-height: 0; }}
    .mi-board-evidence, .mi-board-side {{ min-height: 0; }}
    .mi-board-evidence {{ display: flex; flex-direction: column; }}
    .mi-board-evidence > h3 {{ margin: 0 0 8px; color: #707174; font-size: 13px; letter-spacing: .11em; }}
    .mi-board-news-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); grid-auto-rows: minmax(0, 1fr); gap: 10px; flex: 1; min-height: 0; }}
    .mi-board-news-grid--1 {{ grid-template-columns: 1fr; }}
    .mi-board-news-grid--3 .mi-board-news-card:first-child {{ grid-row: span 2; }}
    .mi-board-news-card {{ display: flex; flex-direction: column; min-height: 0; padding: 13px 15px; border: 1px solid var(--board-border); border-radius: 8px; background: #fff; }}
    .mi-board-news-card h4 {{ margin: 0; font-size: clamp(13px, .94vw, 15px); line-height: 1.24; text-wrap: pretty; }}
    .mi-board-news-card p {{ margin: 7px 0 0; color: #3e4043; font-size: clamp(12px, .88vw, 13px); line-height: 1.3; }}
    .mi-board-news-card .mi-board-signal-connection {{ margin-top: 7px; }}
    .mi-board-news-card .mi-board-signal-connection strong {{ display: block; color: var(--board-red); font-size: clamp(10px, .74vw, 11px); font-weight: 800; line-height: 1.22; }}
    .mi-board-news-card .mi-board-signal-connection span {{ display: block; margin-top: 2px; color: #3e4043; font-size: clamp(10px, .74vw, 11px); font-weight: 400; line-height: 1.22; }}
    .mi-board-news-grid--4 .mi-board-news-card h4 {{ font-size: clamp(12px, .86vw, 13.5px); }}
    .mi-board-news-grid--4 .mi-board-news-card p {{ font-size: clamp(11.2px, .78vw, 12px); line-height: 1.26; }}
    .mi-board-news-grid--4 .mi-board-news-card {{ padding: 9px 11px; }}
    .mi-board-news-grid--4 .mi-board-news-card h4 {{ font-size: 11px; line-height: 1.16; }}
    .mi-board-news-grid--4 .mi-board-news-card p {{ margin-top: 4px; font-size: 9.8px; line-height: 1.17; }}
    .mi-board-news-grid--4 .mi-board-news-card .mi-board-signal-connection strong,
    .mi-board-news-grid--4 .mi-board-news-card .mi-board-signal-connection span {{ font-size: 9.1px; line-height: 1.14; }}
    .mi-board-highlight {{ padding: .05em .14em; border-radius: 3px; color: var(--board-text); background: rgba(229, 0, 43, .16); font-weight: 750; text-decoration: underline 2px var(--board-red); text-underline-offset: 3px; text-decoration-skip-ink: none; box-decoration-break: clone; -webkit-box-decoration-break: clone; }}
    .mi-board-meta {{ display: flex; align-items: baseline; flex-wrap: wrap; gap: 4px 9px; margin-top: auto; padding-top: 7px; }}
    .mi-board-cite {{ display: block; padding-right: 10px; color: #5f6063; font-size: 10.5px; text-decoration: none; }}
    .mi-board-published-date {{ color: #666; font-size: 10.5px; font-weight: 700; white-space: nowrap; }}
    .mi-board-news-grid--4 .mi-board-meta {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 4px; margin-top: auto; padding-top: 3px; }}
    .mi-board-news-grid--4 .mi-board-cite, .mi-board-news-grid--4 .mi-board-published-date {{ font-size: 8.4px; line-height: 1.12; }}
    .mi-board-news-inline-image {{ display: block; height: clamp(78px, 10vh, 118px); margin-top: 9px; overflow: hidden; border: 1px solid var(--board-border); border-radius: 6px; background: #f6f6f5; }}
    .mi-board-news-card--with-image .mi-board-news-inline-image {{ flex: 1 1 auto; height: auto; min-height: 150px; margin: 10px 0; }}
    .mi-board-news-card--with-image .mi-board-meta {{ margin-top: 0; }}
    .mi-board-news-inline-image img {{ width: 100%; height: 100%; object-fit: cover; }}
    .mi-board-news-inline-image[data-news-id="NEWS-MARKET-002"] {{ border-color: #009c55; background: #009c55; }}
    .mi-board-news-inline-image--side {{ padding: 8px; }}
    .mi-board-news-inline-image--side img {{ object-fit: contain; }}
    .mi-board-side {{ display: grid; grid-template-rows: minmax(145px, 1.1fr) minmax(0, .9fr); gap: 10px; }}
    .mi-board-side--without-media {{ grid-template-rows: minmax(0, 1fr); }}
    .mi-board-side--media-after {{ grid-template-rows: auto minmax(0, 1fr); }}
    .mi-board-media-gallery {{ display: grid; min-height: 0; overflow: hidden; gap: 8px; }}
    .mi-board-media-gallery--1 {{ grid-template-columns: 1fr; }}
    .mi-board-media-gallery--2 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .mi-board-media-gallery--3 {{ grid-template-columns: minmax(0, 1.45fr) minmax(0, .85fr); grid-template-rows: repeat(2, minmax(0, 1fr)); }}
    .mi-board-media-gallery--3 .mi-board-media--primary {{ grid-row: span 2; }}
    .mi-board-media {{ position: relative; display: block; min-height: 0; overflow: hidden; border: 1px solid var(--board-border); border-radius: 8px; background: #f6f6f5; }}
    .mi-board-media img {{ position: absolute; inset: 0; width: 100%; height: 100%; min-height: 0; object-fit: cover; }}
    .mi-board-media--side img {{ padding: 16px; object-fit: contain; }}
    .mi-board-ot-stack {{ display: grid; gap: 8px; min-height: 0; }}
    .mi-board-ot {{ padding: 10px 14px; border: 1px solid; border-radius: 8px; }}
    .mi-board-ot strong {{ display: block; margin-bottom: 3px; font-size: 11.8px; }}
    .mi-board-ot p {{ margin: 0; font-size: clamp(12.1px, .9vw, 13.5px); line-height: 1.3; }}
    .mi-board-ot--opportunity {{ color: #07584f; border-color: #91d9c3; background: #ddf5ee; }}
    .mi-board-ot--threat {{ color: #8f201a; border-color: #f4b4b4; background: #fde8e8; }}
    .mi-board-page-b .mi-slide-body {{ grid-template-rows: auto auto; align-content: start; gap: 12px; }}
    .mi-board-page-c h2 {{ max-width: 980px; font-size: clamp(27px, 2.15vw, 33px); }}
    .mi-board-page-c .mi-eyebrow {{ font-size: 9.5px; }}
    .mi-board-reference .mi-slide-body {{ grid-template-rows: minmax(0, 1fr); }}
    .mi-board-reference h2 {{ max-width: 1070px; font-size: clamp(27px, 2.18vw, 34px); }}
    .mi-technology-template {{ display: flex; min-height: 0; padding: 16px; border: 1px solid var(--board-border); border-radius: 8px; background: #fff; }}
    .mi-technology-template .mi-fill-placeholder {{ flex: 1 1 auto; min-height: 0; border: 1px dashed #c9c9c7; border-radius: 6px; background: #fbfbfa; }}
    .mi-technology-waiting {{ display: flex; align-items: center; gap: 10px; padding: 8px 12px; border: 1px solid #efc36b; border-radius: 7px; background: #fff8e6; color: #684700; font-size: 11px; }}
    .mi-technology-waiting strong {{ color: #a46a00; font: 800 10px "VSF Pro", "Lexend", sans-serif; letter-spacing: .08em; }}
    .mi-reference-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); align-items: stretch; gap: 14px; min-height: 0; }}
    .mi-reference-card {{ display: flex; min-width: 0; min-height: 0; flex-direction: column; gap: 9px; padding: 14px 16px; border: 1px solid var(--board-border); border-radius: 9px; background: #fff; }}
    .mi-reference-card .mi-fill-placeholder {{ border: 1px dashed #d1d1cf; border-radius: 5px; background: #fbfbfa; }}
    .mi-reference-field-label {{ color: #6b6c6f; font-size: 9.5px; letter-spacing: .025em; }}
    .mi-reference-title-placeholder {{ min-height: 42px; }}
    .mi-reference-description {{ display: grid; grid-template-rows: auto minmax(0, 1fr); gap: 5px; flex: 1 1 auto; min-height: 80px; color: #3e4043; font-size: 11px; font-weight: 400; line-height: 1.3; }}
    .mi-reference-description .mi-fill-placeholder {{ flex: 1 1 auto; }}
    .mi-reference-scale {{ display: grid; gap: 5px; min-height: 72px; padding: 9px; border-radius: 6px; background: #f5f5f4; font-size: 10.5px; }}
    .mi-reference-scale .mi-fill-placeholder {{ min-height: 30px; background: #fff; }}
    .mi-reference-common {{ display: grid; grid-template-columns: auto minmax(0, 1fr); align-items: center; gap: 8px; min-height: 58px; padding: 10px 14px; border-left: 4px solid var(--board-red); border-radius: 0 8px 8px 0; background: #fff3f3; color: #8f151a; font-size: 11px; }}
    .mi-reference-common .mi-fill-placeholder {{ min-height: 34px; border: 1px dashed #e3a9aa; border-radius: 5px; background: rgba(255,255,255,.68); }}
    .mi-board-market-grid {{ display: grid; grid-template-columns: minmax(0, .92fr) minmax(0, 1.28fr); align-items: stretch; gap: 14px; min-height: 0; }}
    .mi-board-card {{ min-height: 0; overflow: hidden; padding: 14px 18px; border: 1px solid var(--board-border); border-radius: 8px; background: #fff; }}
    .mi-board-card-head {{ display: flex; justify-content: space-between; gap: 16px; margin-bottom: 8px; }}
    .mi-board-card-head h3 {{ margin: 0; color: #707174; font-size: 12px; letter-spacing: .1em; }}
    .mi-board-card-head > strong {{ color: var(--board-red); font-size: 11px; text-align: right; }}
    .mi-board-card > h4 {{ margin: 0 0 8px; font-size: 17.5px; }}
    .mi-board-field {{ margin-top: 7px; }}
    .mi-board-field > strong {{ font-size: 12.6px; }}
    .mi-board-field p {{ margin: 2px 0 0; font-size: clamp(12.6px, .96vw, 14.2px); line-height: 1.32; }}
    .mi-board-list {{ margin: 4px 0 0; padding-left: 17px; }}
    .mi-board-list li {{ margin: 0 0 3px; font-size: clamp(11.8px, .88vw, 13px); line-height: 1.26; }}
    /* Product-gap cards carry the longest approved missing-feature tables. Keep the
       full table inside the fixed 16:9 Page B frame instead of clipping the final row. */
    .mi-board-page-b .mi-board-gap {{ display: flex; flex-direction: column; justify-content: space-between; gap: 9px; padding: 12px 17px; }}
    .mi-board-page-b .mi-board-gap .mi-board-card-head {{ margin-bottom: 0; }}
    .mi-board-page-b .mi-board-gap .mi-board-card-head h3 {{ font-size: 11.5px; }}
    .mi-board-page-b .mi-board-gap .mi-board-card-head > strong {{ font-size: 10.4px; line-height: 1.15; }}
    .mi-board-page-b .mi-board-gap .mi-board-field {{ margin-top: 0; }}
    .mi-board-page-b .mi-board-gap .mi-board-field > strong {{ font-size: 12.1px; }}
    .mi-board-page-b .mi-board-gap .mi-board-field p {{ font-size: clamp(11.6px, .85vw, 12.6px); line-height: 1.22; }}
    .mi-board-page-b .mi-board-gap .mi-board-list {{ margin-top: 2px; padding-left: 16px; }}
    .mi-board-page-b .mi-board-gap .mi-board-list li {{ margin-bottom: 2px; font-size: clamp(10.8px, .79vw, 11.8px); line-height: 1.17; }}
    .mi-gap-reference-head, .mi-gap-reference-line {{ display: grid; grid-template-columns: minmax(0, 1.45fr) minmax(150px, .75fr); gap: 14px; }}
    .mi-gap-reference-head {{ padding: 5px 7px 3px; color: #8a8a88; font: 700 10px/1.15 "VSF Pro", "Lexend", sans-serif; letter-spacing: .035em; }}
    .mi-gap-reference-list {{ min-height: 0; }}
    .mi-gap-reference-line {{ align-items: start; min-height: 30px; padding: 4px 7px; }}
    .mi-gap-reference-line p {{ margin: 0; font-size: clamp(9.8px, .73vw, 10.8px); line-height: 1.18; }}
    .mi-gap-reference-blank {{ display: grid; grid-template-columns: auto minmax(0, 1fr); align-items: start; gap: 5px; min-width: 0; color: #777; font-size: 11px; line-height: 1; }}
    .mi-gap-reference-line .mi-fill-placeholder {{ min-height: 17px; border: 0; border-radius: 0; background: transparent; }}
    .mi-board-gap-table {{ width: 100%; margin-top: 5px; border-collapse: collapse; table-layout: fixed; }}
    .mi-board-gap-table th, .mi-board-gap-table td {{ border-bottom: 1px solid #d7d7d5; padding: 5px 8px; text-align: left; vertical-align: top; }}
    .mi-board-gap-table th {{ color: #8a8a88; font: 700 9.2px/1.15 "VSF Pro", "Lexend", sans-serif; letter-spacing: .035em; }}
    .mi-board-gap-table th:first-child, .mi-board-gap-table td:first-child {{ width: 64%; }}
    .mi-board-gap-table--action th:first-child, .mi-board-gap-table--action td:first-child {{ width: 100%; }}
    .mi-board-gap-table td {{ font-size: clamp(9.8px, .73vw, 10.8px); line-height: 1.18; }}
    .mi-board-gap-reference {{ min-height: 28px; background: #fff; }}
    .mi-board-gap {{ background: #fbfbfa; }}
    .mi-board-action {{ padding: 12px 18px; border: 1px solid var(--board-border); border-radius: 8px; background: #f7f7f6; }}
    .mi-board-action-head {{ margin-bottom: 8px; color: var(--board-red); font: 800 12.5px "VSF Pro", "Lexend", sans-serif; letter-spacing: .035em; }}
    .mi-board-action-gap {{ float: right; color: #555; letter-spacing: 0; }}
    .mi-board-action-grid {{ display: grid; grid-template-columns: 1.05fr 1.15fr 1.1fr; gap: 22px; }}
    .mi-board-action-grid strong {{ font-size: 12.6px; }}
    .mi-board-action-grid p {{ margin: 2px 0 0; font-size: clamp(12.2px, .92vw, 13.5px); line-height: 1.3; }}
    @media (max-width: 900px) {{
      .mi-board-slide {{ height: auto; min-height: 100vh; overflow: visible; padding: 28px 20px 72px; }}
      .mi-board-slide .mi-slide-header, .mi-board-a-grid, .mi-board-market-grid, .mi-board-action-grid, .mi-reference-grid {{ grid-template-columns: 1fr; }}
      .mi-board-slide .mi-logo {{ width: 130px; }}
      .mi-board-news-grid {{ grid-template-columns: 1fr; }}
      .mi-board-news-grid--3 .mi-board-news-card:first-child {{ grid-row: auto; }}
      .mi-keep {{ white-space: normal; }}
      .mi-board-side {{ grid-template-rows: 260px auto; }}
      .mi-board-action-gap {{ display: block; float: none; margin-top: 3px; }}
    }}
    @media (prefers-reduced-motion: reduce) {{ html, .mi-deck {{ scroll-behavior: auto; }} .mi-progress {{ transition: none; }} }}
    @page {{ size: 13.333in 7.5in; margin: 0; }}
    @media print {{
      html, body {{ width: 13.333in; height: auto; background: #fff; }}
      .mi-deck {{ width: 13.333in; height: auto; overflow: visible; }}
      .mi-slide {{ width: 13.333in; height: 7.5in; min-height: 7.5in; max-height: 7.5in; overflow: hidden; break-inside: avoid-page; page-break-inside: avoid; break-after: page; page-break-after: always; contain: size layout paint; padding: .42in .62in .5in; print-color-adjust: exact; -webkit-print-color-adjust: exact; }}
      .mi-slide:last-child {{ break-after: auto; page-break-after: auto; }}
      .mi-cover {{ display: grid; grid-template-columns: minmax(0, 1fr); align-items: center; padding: 44px 52px 44px 76px; }}
      .mi-cover-copy h1 {{ max-width: 560px; font-size: 52px; }}
      .mi-cover-flow {{ width: auto; max-width: none; padding: 28px; }}
      .mi-executive-summary {{ display: flex; }}
      .mi-executive-summary .mi-slide-header {{ grid-template-columns: minmax(0, 1fr) auto; min-height: 88px; margin-bottom: 0; }}
      .mi-executive-summary .mi-slide-body {{ min-height: 0; overflow: hidden; padding-top: 10px; }}
      .mi-executive-summary .mi-exec-list {{ grid-template-rows: repeat(3, minmax(0, 1fr)); gap: 6px; min-height: 0; }}
      .mi-executive-summary .mi-exec-row {{ min-height: 0; overflow: hidden; }}
      .mi-executive-summary .mi-exec-signal, .mi-executive-summary .mi-exec-action {{ padding: 8px 12px; }}
      .mi-executive-summary .mi-exec-action {{ gap: 5px; }}
      .mi-exec-row {{ grid-template-columns: minmax(0, .92fr) 34px minmax(0, 1.08fr); }}
      .mi-exec-signal {{ grid-template-columns: minmax(112px, auto) 1fr; }}
      .mi-exec-action {{ grid-template-columns: minmax(0, 1fr); grid-template-rows: auto minmax(0, 1fr) auto; }}
      .mi-exec-arrow {{ transform: none; }}
      .mi-slide-header .mi-header-copy, .mi-slide-header .mi-logo {{ order: 0; }}
      .mi-board-slide {{ padding: 22px 52px 44px; }}
      .mi-board-slide .mi-slide-header {{ grid-template-columns: minmax(0, 1fr) 136px; }}
      .mi-board-slide .mi-logo {{ width: 136px; }}
      .mi-board-a-grid {{ grid-template-columns: minmax(0, 1.47fr) minmax(340px, .93fr); }}
      .mi-board-market-grid {{ grid-template-columns: minmax(0, .92fr) minmax(0, 1.28fr); }}
      .mi-board-action-grid {{ grid-template-columns: 1.05fr 1.15fr 1.1fr; }}
      .mi-board-news-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .mi-board-news-grid--1 {{ grid-template-columns: 1fr; }}
      .mi-board-news-grid--3 .mi-board-news-card:first-child {{ grid-row: span 2; }}
      .mi-board-news-card--with-image .mi-board-news-inline-image {{ flex: 1 1 auto; height: auto; min-height: 126px; max-height: none; margin: 10px 0; }}
      .mi-board-news-grid--4 {{ gap: 8px; }}
      .mi-board-news-grid--4 .mi-board-news-card {{ padding: 9px 11px; }}
      .mi-board-news-grid--4 .mi-board-news-card h4 {{ font-size: 11px; line-height: 1.16; }}
      .mi-board-news-grid--4 .mi-board-news-card p {{ margin-top: 4px; font-size: 9.8px; line-height: 1.17; }}
      .mi-board-news-grid--4 .mi-board-news-card .mi-board-signal-connection strong,
      .mi-board-news-grid--4 .mi-board-news-card .mi-board-signal-connection span {{ font-size: 9.1px; line-height: 1.14; }}
      .mi-board-news-grid--4 .mi-board-meta {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 4px; margin-top: auto; padding-top: 3px; }}
      .mi-board-news-grid--4 .mi-board-cite, .mi-board-news-grid--4 .mi-board-published-date {{ font-size: 8.4px; line-height: 1.12; }}
      .mi-board-side {{ grid-template-rows: minmax(145px, 1.1fr) minmax(0, .9fr); }}
      .mi-board-side--media-after {{ grid-template-rows: auto minmax(0, 1fr); }}
      .mi-board-action-gap {{ display: inline; float: right; margin-top: 0; }}
      .mi-keep {{ white-space: nowrap; }}
      .mi-approach-layout {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .mi-approach .mi-slide-header {{ position: relative; display: block; min-height: 104px; }}
      .mi-approach .mi-header-copy {{ max-width: calc(100% - 190px); }}
      .mi-approach .mi-logo {{ position: absolute; top: 0; right: 0; width: 154px; }}
      .mi-approach-step {{ grid-template-columns: 36px 170px minmax(0, 1fr); }}
      .mi-response-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .mi-controls, .mi-progress {{ display: none !important; }}
    }}
  </style>
</head>
<body>
  <main class="mi-deck" id="vsf-mi-deck">{slides}</main>
  <div class="mi-progress" id="mi-progress" aria-hidden="true"></div>
  <nav class="mi-controls" aria-label="Điều khiển trình chiếu">
    <button type="button" id="mi-prev" aria-label="Slide trước">←</button>
    <span class="mi-counter" id="mi-counter" aria-live="polite">01 / {total:02d}</span>
    <button type="button" id="mi-next" aria-label="Slide tiếp theo">→</button>
    <button type="button" id="mi-fullscreen" aria-label="Toàn màn hình">⛶</button>
  </nav>
  <p class="sr-only">Dùng phím mũi tên, Page Up, Page Down, Space, Home và End để điều hướng.</p>
  <script>
    (() => {{
      const deck = document.getElementById('vsf-mi-deck');
      const slides = Array.from(deck.querySelectorAll('.mi-slide'));
      const prev = document.getElementById('mi-prev');
      const next = document.getElementById('mi-next');
      const fullscreen = document.getElementById('mi-fullscreen');
      const counter = document.getElementById('mi-counter');
      const progress = document.getElementById('mi-progress');
      const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
      let current = 0;

      const update = (index, syncHash = true) => {{
        current = Math.max(0, Math.min(slides.length - 1, index));
        counter.textContent = String(current + 1).padStart(2, '0') + ' / ' + String(slides.length).padStart(2, '0');
        progress.style.width = ((current + 1) / slides.length * 100) + '%';
        prev.disabled = current === 0;
        next.disabled = current === slides.length - 1;
        slides.forEach((slide, i) => slide.setAttribute('aria-current', i === current ? 'true' : 'false'));
        if (syncHash) history.replaceState(null, '', '#slide-' + (current + 1));
      }};

      const go = (index) => {{
        const target = Math.max(0, Math.min(slides.length - 1, index));
        slides[target].scrollIntoView({{ behavior: reducedMotion.matches ? 'auto' : 'smooth', block: 'start' }});
        update(target);
      }};

      prev.addEventListener('click', () => go(current - 1));
      next.addEventListener('click', () => go(current + 1));
      fullscreen.addEventListener('click', async () => {{
        if (!document.fullscreenElement && document.documentElement.requestFullscreen) await document.documentElement.requestFullscreen();
        else if (document.exitFullscreen) await document.exitFullscreen();
      }});

      document.addEventListener('keydown', (event) => {{
        if (event.target.closest('input, textarea, select, button, a')) return;
        if (['ArrowRight', 'ArrowDown', 'PageDown', ' '].includes(event.key)) {{ event.preventDefault(); go(current + 1); }}
        else if (['ArrowLeft', 'ArrowUp', 'PageUp'].includes(event.key)) {{ event.preventDefault(); go(current - 1); }}
        else if (event.key === 'Home') {{ event.preventDefault(); go(0); }}
        else if (event.key === 'End') {{ event.preventDefault(); go(slides.length - 1); }}
      }});

      const observer = new IntersectionObserver((entries) => {{
        const visible = entries.filter(entry => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) update(Number(visible.target.dataset.index));
      }}, {{ root: deck, threshold: [0.55, 0.75] }});
      slides.forEach(slide => observer.observe(slide));

      const requested = Number((location.hash.match(/slide-(\\d+)/) || [])[1]);
      if (Number.isInteger(requested) && requested >= 1 && requested <= slides.length) go(requested - 1);
      else update(0, false);
    }})();
  </script>
</body>
</html>
"""


def validate_html(output: Path, expected_slides: int) -> None:
    text = output.read_text(encoding="utf-8")
    actual = len(re.findall(r'<section class="mi-slide\b', text))
    if actual != expected_slides:
        raise ValueError(f"HTML validation failed: expected {expected_slides} slides, found {actual}")
    if "data:image/" not in text:
        raise ValueError("HTML validation failed: logo was not embedded")
    if text.count("data:font/ttf;base64,") != 2:
        raise ValueError("HTML validation failed: VSF Pro and Lexend were not both embedded")
    if text.count("data-ppt-slide") != expected_slides:
        raise ValueError("HTML validation failed: every slide must be annotated for editable PowerPoint export")
    if (expected_slides - 3) % 3:
        raise ValueError("HTML validation failed: slide count does not match the three-slide Finding contract")
    expected_findings = (expected_slides - 3) // 3
    if len(re.findall(r'<section class="mi-slide[^"]*\bmi-board-reference\b', text)) != expected_findings:
        raise ValueError("HTML validation failed: each Finding requires one technology-solution placeholder slide")
    if len(re.findall(r'<div class="mi-gap-reference-list"', text)) != expected_findings:
        raise ValueError("HTML validation failed: each Finding requires one missing-feature reference list")
    if len(re.findall(r'<span class="mi-fill-placeholder mi-exec-technology-placeholder"', text)) != expected_findings:
        raise ValueError("HTML validation failed: each Executive Summary row requires one technology-solution placeholder")
    if len(re.findall(r'data-ppt-placeholder="technology-signal-\d+-content"', text)) != expected_findings:
        raise ValueError("HTML validation failed: each technology slide requires one free-form placeholder")
    if text.count("data-ppt-placeholder=") < expected_findings * 2:
        raise ValueError("HTML validation failed: required blank fill-in placeholders are incomplete")
    cover = re.search(r'<section class="mi-slide[^>]*id="slide-1"[^>]*>(.*?)</section>', text, re.DOTALL)
    if cover is None:
        raise ValueError("HTML validation failed: cover slide is missing")
    cover_html = cover.group(1)
    required_cover_copy = (
        "VSF MARKET INTELLIGENCE",
        "Market Intelligence<br>Report",
        "Phòng Nghiên cứu thị trường và Trải nghiệm khách hàng",
    )
    if any(value not in cover_html for value in required_cover_copy):
        raise ValueError("HTML validation failed: fixed cover copy is incomplete")
    if "mi-cover-metadata" in cover_html or "FROM SIGNAL TO ACTION" in cover_html:
        raise ValueError("HTML validation failed: cover contains retired metadata or stage panel")
    if not re.search(r"Tuần \d+ - Tháng \d+ \(\d{2}/\d{2}/\d{4} – \d{2}/\d{2}/\d{4}\)", cover_html):
        raise ValueError("HTML validation failed: cover period label is invalid")
    for forbidden in ("<script src=", "<link rel=\"stylesheet\"", "fetch(", "XMLHttpRequest", "WebSocket"):
        if forbidden in text:
            raise ValueError(f"HTML validation failed: external or network dependency found: {forbidden}")
    required_ids = ("vsf-mi-deck", "mi-prev", "mi-next", "mi-fullscreen", "mi-counter", "mi-progress")
    missing = [value for value in required_ids if f'id="{value}"' not in text]
    if missing:
        raise ValueError("HTML validation failed: missing controls: " + ", ".join(missing))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Approved MI summary Markdown")
    parser.add_argument("--output", type=Path, help="Destination .html path")
    parser.add_argument("--logo", type=Path, help="Approved VSF logo PNG")
    parser.add_argument(
        "--source-deck",
        type=Path,
        help="Existing approved HTML deck providing cover copy, News subtitles, and exact highlights",
    )
    parser.add_argument(
        "--exclude-news-id",
        action="append",
        default=[],
        help="Hide one News ID from the presentation only; repeat for multiple IDs",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input.resolve()
    if not input_path.is_file():
        raise SystemExit(f"Input not found: {input_path}")
    run_root = find_run_root(input_path)
    approved_run_id = validate_gates(run_root)
    report = parse_report(input_path)
    if report.run_id and report.run_id != approved_run_id:
        raise SystemExit(f"Run ID mismatch: report={report.run_id}, manifest={approved_run_id}")
    logo = (args.logo or (Path(__file__).resolve().parent.parent / "assets" / "vsf-logo-transparent.png")).resolve()
    if not logo.is_file():
        raise SystemExit(f"Logo not found: {logo}")
    missing_fonts = [path for path in (HEADING_FONT_PATH, BODY_FONT_PATH) if not path.is_file()]
    if missing_fonts:
        raise SystemExit("Font assets not found: " + ", ".join(str(path) for path in missing_fonts))
    output = args.output.resolve() if args.output else (
        run_root / "deliverables" / "slides" / "market-intelligence-finding-board.html"
    )
    if output.suffix.lower() != ".html":
        raise SystemExit("Output path must end with .html")
    output.parent.mkdir(parents=True, exist_ok=True)

    excluded_news_ids = {clean_atom(item).upper() for item in args.exclude_news_id if clean_atom(item)}
    news_images = discover_news_images(output.parent / "assets")
    source_deck = args.source_deck.resolve() if args.source_deck else None
    if source_deck and not source_deck.is_file():
        raise SystemExit(f"Source deck not found: {source_deck}")
    overlay = load_presentation_overlay(source_deck) if source_deck else None
    news_dates = load_approved_news_dates(run_root)
    builder = HtmlDeckBuilder(report, logo_data_uri(logo), approved_run_id, excluded_news_ids, news_images, overlay, news_dates)
    document = normalize_customer_copy(builder.build())
    if overlay:
        expected_highlights = sum(
            len(record.get("highlights", []))
            for news_id, record in overlay.news.items()
            if news_id not in excluded_news_ids
        )
        actual_highlights = document.count('<mark class="mi-board-highlight">')
        if actual_highlights != expected_highlights:
            raise ValueError(
                f"Presentation overlay mismatch: expected {expected_highlights} highlights, found {actual_highlights}"
            )
    output.write_text(document, encoding="utf-8", newline="\n")
    validate_html(output, len(builder.slides))
    print(json.dumps({
        "output": str(output),
        "format": "html",
        "theme": "finding-board",
        "slides": len(builder.slides),
        "run_id": approved_run_id,
        "gate_check": "APPROVED",
        "self_contained": True,
        "fonts": {"heading": "VSF Pro", "body": "Lexend"},
        "excluded_news_ids": sorted(excluded_news_ids),
        "embedded_news_images": sorted(builder.embedded_news_images),
        "source_deck": str(overlay.source_path) if overlay else None,
        "source_deck_highlights": actual_highlights if overlay else 0,
        "fill_in_placeholders": document.count('data-ppt-placeholder='),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
