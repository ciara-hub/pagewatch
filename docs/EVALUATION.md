# PageWatch — Báo cáo thử nghiệm trên fanpage Juhoonity

Ngày thử nghiệm: **24/10/2026**. Múi giờ trình bày: **Việt Nam, UTC+7**.

## 1. Kết quả chính

Đã đối chiếu trực tiếp năm tệp `reports/bai-1.md` đến `reports/bai-5.md` trong Codespace PageWatch. Chúng tương ứng với **5 bài đăng khác nhau**, có tổng cộng **69 bình luận văn bản được API trả về và được phân tích**. Cả năm phần quét bài đăng có `Status: ok` và `Comment access: ok` trong phạm vi được mô tả bên dưới.

Các mẫu bài đăng ghi nhận **1 finding mức `info`**, thuộc quy tắc `unlisted-domain`; không ghi nhận finding mức `review` hoặc `high`. Mẫu inbox riêng có **5 cuộc trò chuyện, 47 tin nhắn nhận được, 16 tin nhắn văn bản đến được phân tích**, trạng thái `limited`, không có finding trong phần đã phân tích.

Kết quả này chứng minh công cụ đã đọc và phân tích được các mẫu thực tế trong phạm vi API cho phép. **Chưa đủ cơ sở để kết luận toàn bộ Page không có spam, thông tin sai hoặc sự cố bảo mật; chưa có dữ liệu gán nhãn để tính precision/recall.**

## 2. Mục tiêu, nguồn bằng chứng và cách đối chiếu

Thử nghiệm đánh giá ba khả năng của nguyên mẫu Python: lưu/so sánh caption; ghi nhận dấu hiệu cần kiểm tra trong bình luận; và rà soát một mẫu tin nhắn văn bản gửi đến Page. Đây là dự án phòng vệ hỗ trợ admin, không phải một cuộc kiểm thử xâm nhập Facebook hay hệ thống xác minh tính đúng sai của tin tức.

| Hạng mục | Bằng chứng và phạm vi xác minh |
|---|---|
| Nguồn kết quả | Năm báo cáo có sẵn trong Codespace của dự án, repository `ciara-hub/pagewatch`; không chạy lại API để thay thế các kết quả này khi tổng hợp. |
| Danh tính bài đăng | Đối chiếu `Target ref` với hàm tạo tham chiếu trong `pagewatch/analyze.py` và các post ID đã xác nhận từ link công khai. Không suy ra danh tính bài chỉ từ tên tệp. |
| Phạm vi quản lý | Chủ dự án cho biết đang quản lý fanpage Juhoonity và yêu cầu thử nghiệm trên các bài hiện có. Báo cáo này không xác nhận sự đồng ý riêng của từng người bình luận/nhắn tin. |
| Graph version | Cấu hình được sử dụng trong quá trình thiết lập trước đó là `v26.0`; các tệp report không lưu trường version để đối chiếu riêng từng lần quét. |
| Commit nguồn / cấp truy cập Meta | Report không lưu commit SHA, quyền token hoặc cấp truy cập ứng dụng; các thông tin này chưa được xác minh riêng cho từng mẫu. |
| Giới hạn lệnh đã hướng dẫn | `--comments 50 --lookup 500`; report không ghi lại tham số CLI, nên không coi đây là bằng chứng độc lập về tham số thực thi của từng lần quét. |
| Quyền riêng tư | Chỉ tổng hợp số lượng, mã tham chiếu, loại quy tắc và link bài đăng công khai. Không chép nội dung inbox, tên/ID người gửi hoặc access token. |

Các tệp trong `reports/` là bằng chứng cục bộ, đang được `.gitignore` loại khỏi Git. Các đường dẫn nêu trong tài liệu dùng để tìm lại trong Codespace, không phải các tệp đã được công bố trên GitHub.

## 3. Kết quả của năm bài đăng

Thứ tự dưới đây theo **tên tệp thực tế đã lưu**. Bài JUNERY nằm trong `bai-3.md`.

| Tệp nguồn | Bài đăng công khai | Target ref | Giờ quét, 24/10/2026 (UTC+7) | Nhận / phân tích / bỏ qua | Finding |
|---|---|---|---|---|---|
| `reports/bai-1.md` | [Mass trending cho Juhoon — Day 1](https://www.facebook.com/61579488621852/posts/122191534670982954) | `db8ce1da7304` | 15:27:27 | 18 / 18 / 0 | 0 |
| `reports/bai-2.md` | [Thông báo đóng quỹ Protect Juhoon](https://www.facebook.com/61579488621852/posts/122191465526982954) | `68f6e92729c7` | 15:28:33 | 10 / 10 / 0 | 0 |
| `reports/bai-3.md` | [JUNERY — Tiệm bánh nhà Jun](https://www.facebook.com/61579488621852/posts/122184173258982954) | `2af02eb9328b` | 15:31:47 | 17 / 17 / 0 | 1 `info` |
| `reports/bai-4.md` | [Kim Juhoon quyết tâm không bỏ rơi bộ môn nào phía sau](https://www.facebook.com/61579488621852/posts/122191891574982954) | `3762999b3e82` | 15:30:27 | 18 / 18 / 0 | 0 |
| `reports/bai-5.md` | [Bài về bảng xếp hạng danh tiếng thương hiệu của Juhoon](https://www.facebook.com/61579488621852/posts/122192098364982954) | `892a8e9880db` | 15:32:06 | 6 / 6 / 0 | 0 |
| **Tổng của 5 bài khác nhau** | | | | **69 / 69 / 0** | **1 `info`; 0 `review`; 0 `high`** |

“Nhận” là `comments_received`; “phân tích” là `text_comments_analyzed`; “bỏ qua” là `nontext_or_empty_skipped`. Mỗi bài được tính một lần theo bản report này. Những lần quét khác trước đó không được cộng thêm vào mẫu 69 bình luận.

Thời gian UTC gốc lần lượt là `08:27:27`, `08:28:33`, `08:31:47`, `08:30:27`, `08:32:06` ngày 24/10/2026. Đây là mốc ghi nhận kết quả, không phải phép đo tốc độ hay thời gian chạy của từng lệnh.

### Caption và nội dung đính kèm

| Bài / tệp | Ghi nhận thực tế | Điều chưa được kiểm chứng |
|---|---|---|
| Mass trending, đóng quỹ, bài về các bộ môn và bài BXH (`bai-1`, `bai-2`, `bai-4`, `bai-5`) | Caption hiển thị lần đầu được lưu làm baseline. | Không chứng minh caption chưa từng bị sửa trước lúc lưu. |
| JUNERY (`bai-3`) | Caption khớp baseline đã lưu. | Không xác định ai từng chỉnh sửa; không so sánh poster, ảnh hoặc tệp đính kèm. |

Đợt thử nghiệm này sử dụng bài đã đăng; không tạo bài thử hoặc sửa nội dung công khai của Page. Chu trình “sửa caption có chủ đích → phát hiện diff → chấp nhận thay đổi” chưa được kiểm chứng bằng các báo cáo thực tế này.

### Diễn giải finding duy nhất

Trong `bai-3.md`, công cụ ghi nhận:

- Mức độ: `info`.
- Quy tắc: `unlisted-domain`.
- Tham chiếu finding: `def817d27026`.
- Host được nhắc tới: `www.facebook.com`.
- Lý do: host chưa nằm trong danh sách domain tin cậy của dự án.

Đây là thông tin về cấu hình allowlist, **không phải kết luận link lừa đảo**. Finding cũng không cung cấp bằng chứng về thông tin sai hay tài khoản bị chiếm quyền. Chưa có nhãn thủ công cho mục tương ứng, nên chưa tính nó là false positive hoặc true positive. Trường hợp này cho thấy cần tách ghi nhận `info` khỏi cảnh báo spam cần xử lý.

## 4. Mẫu inbox — chỉ tính một lần

Phần inbox trong cả năm file có cùng thời điểm **24/10/2026 07:12:43 UTC**, tức **14:12:43 UTC+7**, và cùng số liệu. Đây là **một mẫu inbox của Page**, không phải năm lần quét độc lập, cũng chưa được chứng minh là tin nhắn liên quan riêng đến năm bài đăng trên.

| Chỉ số | Giá trị |
|---|---:|
| Trạng thái | `limited` |
| `conversations_received` | 5 |
| `messages_received` | 47 |
| `inbound_text_analyzed` | 16 |
| `outgoing_skipped` | 24 |
| `unknown_sender_skipped` | 0 |
| `nontext_skipped` | 7 |
| `failed_reads` | 0 |
| Finding trong mẫu đã phân tích | 0 |

Đối chiếu số học: **16 + 24 + 0 + 7 = 47**. Chỉ 16 tin nhắn văn bản đến được phân tích; 24 tin gửi đi và 7 mục không phải văn bản được bỏ qua. Không có lượt đọc thất bại được ghi nhận trong mẫu này.

Report có ghi `Item limit reached`. Công cụ chỉ lấy những cuộc trò chuyện API nhìn thấy và batch tin nhắn đầu tiên được yêu cầu cho mỗi cuộc trò chuyện; không bảo đảm đọc hết lịch sử hoặc các thư mục Spam/Requests. `failed_reads: 0` không loại bỏ giới hạn lấy mẫu này.

Phần đối chiếu chéo của cả năm báo cáo ghi không có shared unlisted host trong các mẫu đủ điều kiện so sánh trong 24 giờ. Điều này không chứng minh không có liên hệ hoặc chiến dịch spam trên toàn Page.

## 5. Số bình luận trên Facebook và số API trả về

Với bài JUNERY, admin quan sát giao diện Facebook hiển thị **23 bình luận**, trong khi report phân tích **17**. Report nêu rõ chỉ lấy **bình luận cấp đầu API trả về**, không duyệt các câu trả lời lồng bên dưới.

Một cách giải thích có thể là bộ đếm Facebook bao gồm cả replies, nhưng phép đối chiếu từng comment/reply chưa được ghi nhận. Vì vậy **chưa kết luận chênh lệch 6 mục chính là 6 replies**. Thời điểm quan sát và phạm vi dữ liệu nhìn thấy cũng cần được kiểm tra khi đối chiếu tiếp.

Không tính `17/23` thành độ chính xác, recall hay tỷ lệ bao phủ: hai số có thể khác phạm vi. Tương tự, `Status: ok` thể hiện lần đọc hoàn tất trong phạm vi yêu cầu, không xác nhận công cụ nhìn thấy mọi bình luận trên nền tảng.

## 6. Quy tắc, đánh giá chất lượng và giới hạn

Cấu hình `policy.json` được đọc trực tiếp trong Codespace khi tổng hợp: `trusted_domains` rỗng; `repeat_threshold` bằng 3; hai câu được miễn kiểm tra lặp là “Juhoon fighting!” và “Chúc Juhoon một ngày vui vẻ!”. Report không lưu phiên bản policy theo từng lần chạy.

Chưa có bảng gán nhãn thủ công cho 69 bình luận hoặc 16 tin nhắn văn bản đến. Chưa có đối chiếu độc lập từng finding với quyết định của admin. Do đó:

| Chỉ số đánh giá | Kết quả hiện tại |
|---|---|
| TP / FP / FN / TN | Chưa xác định |
| Precision / recall / F1 | Chưa tính |
| False positive được xác nhận | Chưa có bằng chứng gán nhãn; finding `info` ở JUNERY là tình huống cần xem xét, không tự động là FP. |
| Phát hiện spam/lừa đảo thực tế được xác nhận | Chưa có bằng chứng xác nhận trong đợt thử nghiệm này. |
| Độ đúng của tin tức hoặc số liệu trong bài đăng | Chưa đánh giá; công cụ không kiểm chứng nguồn tin. |

Giới hạn có tác động trực tiếp đến cách đọc kết quả:

1. Chỉ phân tích văn bản API trả về; chưa đọc replies, OCR nội dung ảnh, poster, video hoặc tệp đính kèm.
2. Inbox là mẫu giới hạn; không suy rộng sang mọi người gửi, mọi thư mục và toàn bộ lịch sử.
3. Quy tắc theo dấu hiệu có thể bỏ sót spam và ghi nhận tương tác fan hợp lệ. Bình luận lặp trong chiến dịch trending cần được xem trong ngữ cảnh.
4. Token, quyền ứng dụng và quyền quản lý Page có thể làm thay đổi dữ liệu truy cập được giữa các lần chạy. Lần chạy lỗi token không được coi là kết quả “không có finding”.
5. Chưa có chức năng chặn người ngoài truy cập tài liệu nội bộ, ngăn rò rỉ thiết kế, tự xóa/chặn bình luận hay gửi cảnh cáo tự động cho admin. Các chức năng đó không được tuyên bố là đã kiểm chứng bởi báo cáo này.

## 7. Kiểm thử tổng hợp và kết quả thực tế

| Loại bằng chứng | Nội dung | Cách sử dụng |
|---|---|---|
| Kết quả thực tế | 5 bài, 69 bình luận văn bản; 1 mẫu inbox có 16 tin nhắn văn bản đến được phân tích. | Đánh giá khả năng tích hợp và mô tả giới hạn trên các mẫu đã đọc. |
| Kiểm thử tự động bằng dữ liệu tổng hợp | Hồ sơ [VERIFICATION.md](../VERIFICATION.md) đã ghi nhận 38 kiểm thử offline chạy thành công. | Kiểm tra hành vi mã với các tình huống được xây dựng; không dùng làm tỷ lệ phát hiện spam thực tế. |
| Demo tổng hợp | `reports/demo.md`, được giữ riêng. | Không cộng vào bảng năm bài hoặc số liệu inbox ở trên. |

Lần cập nhật tài liệu này không thực hiện một đợt kiểm thử mã mới. Chưa có thử nghiệm có kiểm soát về thay đổi caption trên bài công khai trong mẫu thực tế; các tình huống đó cần tiếp tục dùng dữ liệu tổng hợp hoặc môi trường thử nghiệm được phép.

## 8. Bài học và bước tiếp theo

Bối cảnh quản lý hai fanpage giúp chủ dự án chọn một vấn đề thực tế: admin cần xem nhanh những dấu hiệu đáng kiểm tra, nhưng phải phân biệt spam với cách tương tác thường gặp trong cộng đồng fan. Đợt thử nghiệm cho thấy tích hợp API và giải thích phạm vi dữ liệu là một phần thiết yếu của công cụ bảo mật, không chỉ là số finding được tạo ra.

Finding về `www.facebook.com` cho thấy nhãn “chưa nằm trong allowlist” cần được trình bày đúng nghĩa. Việc inbox lặp lại trong năm báo cáo cũng cho thấy phải đối chiếu timestamp để tránh cộng trùng mẫu và phóng đại quy mô thử nghiệm.

Phạm vi thực nghiệm đã thực hiện gồm xác định yêu cầu từ công việc quản lý fanpage, thiết lập ứng dụng Meta, cấu hình môi trường và chạy thử trên Page. Các kết luận trong tài liệu dựa trên số liệu của các báo cáo đã lưu.

Các bước đánh giá tiếp theo, chưa được tính là đã hoàn thành:

1. Đối chiếu bình luận cấp đầu và replies của một bài, theo ID và cùng thời điểm, để kiểm tra chênh lệch với bộ đếm Facebook.
2. Gán nhãn thủ công một mẫu được phép sử dụng: nghi spam, hợp lệ, chưa rõ. Quy định trước `review/high` là cảnh báo dương tính; theo dõi `info` riêng. Loại mục “chưa rõ” khỏi chỉ số nhị phân và báo cáo số lượng đó.
3. Khi có nhãn, tính precision = TP/(TP+FP) và recall = TP/(TP+FN) nếu mẫu số khác 0; mô tả đây là mức khớp với nhãn trong mẫu truy cập được.
4. Bổ sung timestamp, URL hoặc post ID được bảo vệ phù hợp, commit SHA, Graph version và bản policy vào metadata từng lần quét để truy vết tốt hơn.
5. Thử nghiệm caption thay đổi bằng dữ liệu tổng hợp; chỉ mở rộng tính năng sau khi có tiêu chí kiểm tra và bằng chứng riêng.

**Kết luận:** PageWatch đã có bằng chứng chạy trên năm bài thật và một mẫu inbox thật, với số liệu nhận/phân tích/bỏ qua rõ ràng. Đợt thử nghiệm hiện xác nhận khả năng đọc và rà soát mẫu trong phạm vi API; chất lượng phát hiện spam, kiểm chứng thông tin và khả năng bảo vệ tài liệu nội bộ vẫn cần được đánh giá hoặc phát triển thêm.
