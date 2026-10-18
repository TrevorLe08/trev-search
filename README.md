<a id="readme-top"></a>

[![MIT License][license-shield]][license-url]

<br />
<div align="center">
  <a href="https://github.com/TrevorLe08/trev-search">
    <img src="https://res.cloudinary.com/rnusmvyi/image/upload/v1792293772/logo-trev-search.png" alt="Trev Search logo" width="150" height="150">
  </a>

<h3 align="center">Trev Search</h3>

  <p align="center">
    A plugin for Google Antigravity: web search with inspected, visible sources.
    <br />
    Plugin cho Google Antigravity: tìm kiếm web với nguồn được kiểm tra và hiển thị rõ ràng.
    <br />
    <br />
    <a href="#about-the-project"><strong>English</strong></a>
    &middot;
    <a href="#giới-thiệu-dự-án"><strong>Tiếng Việt</strong></a>
  </p>
</div>

<details>
  <summary>Table of Contents / Mục lục</summary>
  <ol>
    <li><a href="#about-the-project">About The Project</a></li>
    <li><a href="#getting-started">Getting Started</a></li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#giới-thiệu-dự-án">Tiếng Việt</a></li>
  </ol>
</details>

<!-- ENGLISH -->

## About The Project

Trev Search is a plugin for [Google Antigravity](https://antigravity.google/). It answers a question, finds links for you to read yourself, or fact-checks content you supply, quickly or in depth. Every claim points back to a page that was actually opened.

| Command | What it does |
| :--- | :--- |
| `/search` | Concise sourced answer on any topic. |
| `/search-url` | Finds credible, opened and verified links to read yourself. No generated answer. |
| `/search-check-fast` | Fact-checks supplied content (links, numbers, dates, quotes, names, images) against original sources. |
| `/search-check-deep` | Thorough fact-check of a long text: every checkable claim, internal consistency, misleading context, the text's own citations. |
| `/search-deep` | Deep multi-angle search. Asks first how many sources, which research style and whether to add illustration images. |
| `/search-help` | Explains the modes and recommends the one that fits your need. Runs no search. |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Getting Started

Install it with the Antigravity CLI (`agy`):

```bash
agy plugin install https://github.com/TrevorLe08/trev-search
```

The repository root is the plugin: `plugin.json`, `skills/` and `commands/`.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Usage

- `/search What is the latest stable version of Node.js?`
- `/search-url Official guidance on vitamin D dosage`
- `/search-check-fast Is this quote really from the article it cites? <paste text>`
- `/search-deep History of the Mekong Delta salinity intrusion`

Not sure which command to use? Run `/search-help`.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Contact

Trevor Le - [@TrevorLe08](https://github.com/TrevorLe08)

Built by Trevor Le with assistance from Claude (Anthropic).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<!-- TIẾNG VIỆT -->

## Giới thiệu dự án

Trev Search là plugin cho [Google Antigravity](https://antigravity.google/). Plugin trả lời câu hỏi, tìm link để bạn tự đọc, hoặc kiểm chứng nội dung bạn đưa vào, nhanh hoặc chuyên sâu. Mỗi nhận định đều dẫn về một trang đã thực sự được mở ra xem.

| Lệnh | Chức năng |
| :--- | :--- |
| `/search` | Trả lời ngắn gọn, có nguồn, về mọi chủ đề. |
| `/search-url` | Chỉ tìm các link uy tín đã mở và kiểm tra để bạn tự đọc. Không viết câu trả lời. |
| `/search-check-fast` | Kiểm chứng nhanh nội dung bạn đưa (link, số liệu, ngày tháng, trích dẫn, tên, hình ảnh) với nguồn gốc. |
| `/search-check-deep` | Kiểm chứng kỹ một văn bản dài: từng nhận định kiểm tra được, tính nhất quán nội bộ, ngữ cảnh gây hiểu lầm, các trích dẫn của chính văn bản. |
| `/search-deep` | Tìm kiếm sâu nhiều góc độ. Hỏi trước số lượng nguồn, phong cách nghiên cứu và có thêm ảnh minh hoạ hay không. |
| `/search-help` | Giải thích các chế độ và gợi ý lệnh phù hợp với nhu cầu. Không chạy tìm kiếm. |

<p align="right">(<a href="#readme-top">về đầu trang</a>)</p>

## Bắt đầu

Cài bằng Antigravity CLI (`agy`):

```bash
agy plugin install https://github.com/TrevorLe08/trev-search
```

Thư mục gốc của repo chính là plugin: `plugin.json`, `skills/` và `commands/`.

<p align="right">(<a href="#readme-top">về đầu trang</a>)</p>

## Cách dùng

- `/search Giá vàng SJC hôm nay là bao nhiêu?`
- `/search-url Hướng dẫn chính thức về liều vitamin D`
- `/search-check-fast Câu trích này có thật sự nằm trong bài báo nó dẫn không? <dán văn bản>`
- `/search-deep Lịch sử xâm nhập mặn ở đồng bằng sông Cửu Long`

Chưa biết dùng lệnh nào? Chạy `/search-help`.

<p align="right">(<a href="#readme-top">về đầu trang</a>)</p>

## Giấy phép

Phát hành theo Giấy phép MIT. Xem [`LICENSE`](LICENSE) để biết thêm.

<p align="right">(<a href="#readme-top">về đầu trang</a>)</p>

## Liên hệ

Trevor Le - [@TrevorLe08](https://github.com/TrevorLe08)

Do Trevor Le xây dựng, với sự hỗ trợ của Claude (Anthropic).

<p align="right">(<a href="#readme-top">về đầu trang</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
[license-shield]: https://img.shields.io/github/license/TrevorLe08/trev-search.svg?style=for-the-badge
[license-url]: https://github.com/TrevorLe08/trev-search/blob/main/LICENSE
