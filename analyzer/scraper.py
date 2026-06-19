import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import json


def scrape_page(url: str) -> dict:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')

        # タイトル
        title_tag = soup.find('title')
        title = title_tag.get_text().strip() if title_tag else ''

        # メタディスクリプション
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        meta_description = meta_desc.get('content', '').strip() if meta_desc else ''

        # 見出し
        headings = {}
        for level in range(1, 7):
            tags = soup.find_all(f'h{level}')
            headings[f'h{level}'] = [tag.get_text().strip() for tag in tags]

        # 画像
        all_images = soup.find_all('img')
        images_without_alt = sum(1 for img in all_images if not img.get('alt', '').strip())

        # リンク
        parsed_url = urlparse(url)
        base_domain = parsed_url.netloc
        internal_links = set()
        external_links = set()
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            if href.startswith('http'):
                if base_domain in href:
                    internal_links.add(href)
                else:
                    external_links.add(href)
            elif href.startswith('/') and href != '/':
                internal_links.add(urljoin(url, href))

        # 構造化データ
        schema_scripts = soup.find_all('script', attrs={'type': 'application/ld+json'})
        has_schema = len(schema_scripts) > 0
        schema_types = []
        for script in schema_scripts:
            try:
                data = json.loads(script.string or '')
                if '@type' in data:
                    schema_types.append(data['@type'])
                elif '@graph' in data:
                    for item in data['@graph']:
                        if '@type' in item:
                            schema_types.append(item['@type'])
            except Exception:
                pass

        # テキスト量
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        text_content = soup.get_text(separator=' ', strip=True)
        word_count = len(text_content.split())

        # FAQ判定
        has_faq = any(kw in text_content for kw in ['よくある質問', 'FAQ', 'Q&A', 'よくあるご質問'])

        # Canonical
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        has_canonical = canonical is not None

        # SSL
        is_ssl = url.startswith('https://')

        # OGP
        og_title = soup.find('meta', attrs={'property': 'og:title'})
        has_ogp = og_title is not None

        # viewport
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        has_viewport = viewport is not None

        # 会社・連絡先情報
        contact_keywords = ['電話', 'お問い合わせ', 'contact', 'メール', 'mail', 'tel:', '住所', '所在地']
        has_contact = any(kw.lower() in text_content.lower() for kw in contact_keywords)

        # サービス・会社情報
        about_keywords = ['会社概要', 'about', 'サービス', '事業内容', '私たちについて']
        has_about = any(kw.lower() in text_content.lower() for kw in about_keywords)

        return {
            'url': url,
            'title': title,
            'title_length': len(title),
            'meta_description': meta_description,
            'meta_description_length': len(meta_description),
            'headings': headings,
            'h1_count': len(headings.get('h1', [])),
            'h1_texts': headings.get('h1', []),
            'h2_texts': headings.get('h2', []),
            'total_images': len(all_images),
            'images_without_alt': images_without_alt,
            'internal_links_count': len(internal_links),
            'external_links_count': len(external_links),
            'has_schema': has_schema,
            'schema_types': schema_types,
            'word_count': word_count,
            'has_faq': has_faq,
            'has_canonical': has_canonical,
            'is_ssl': is_ssl,
            'has_ogp': has_ogp,
            'has_viewport': has_viewport,
            'has_contact': has_contact,
            'has_about': has_about,
        }

    except requests.exceptions.SSLError:
        return {'error': 'SSL証明書エラー。URLを確認してください。', 'url': url}
    except requests.exceptions.ConnectionError:
        return {'error': 'サイトに接続できませんでした。URLを確認してください。', 'url': url}
    except requests.exceptions.Timeout:
        return {'error': 'タイムアウト。サイトの応答が遅すぎます。', 'url': url}
    except Exception as e:
        return {'error': str(e), 'url': url}
