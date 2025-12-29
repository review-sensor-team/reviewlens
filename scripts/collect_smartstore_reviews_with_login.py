#!/usr/bin/env python3
"""
네이버 스마트스토어 리뷰 수집 (로그인 지원)

로그인 후 리뷰를 수집합니다.

사용법:
    python scripts/collect_smartstore_reviews_with_login.py <product_url> [옵션]

예시:
    python scripts/collect_smartstore_reviews_with_login.py \\
        "https://smartstore.naver.com/shop/products/123" \\
        --category electronics \\
        --product-name product_name \\
        --naver-id "your_id" \\
        --naver-pw "your_password" \\
        --max-reviews 50
"""

import argparse
import json
import re
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import hashlib
import getpass

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.keys import Keys
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

import pandas as pd


def normalize_text(text: str) -> str:
    """텍스트 정규화"""
    if not text:
        return ""
    
    text = text.replace('\n', ' ').replace('\r', ' ')
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
    
    return text


class SmartStoreReviewCollectorWithLogin:
    """네이버 스마트스토어 리뷰 수집 (로그인 지원)"""
    
    def __init__(self, product_url: str, naver_id: str = None, naver_pw: str = None, headless: bool = False):
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium이 설치되어 있지 않습니다. pip install selenium webdriver-manager")
        
        self.product_url = product_url
        self.product_id = self._extract_product_id(product_url)
        self.naver_id = naver_id
        self.naver_pw = naver_pw
        self.driver = self._init_driver(headless)
        
    def _extract_product_id(self, url: str) -> str:
        """URL에서 상품 ID 추출"""
        match = re.search(r'/products/(\d+)', url)
        if not match:
            raise ValueError(f"상품 ID를 찾을 수 없습니다: {url}")
        return match.group(1)
    
    def _init_driver(self, headless: bool):
        """Chrome 드라이버 초기화"""
        options = Options()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # 봇 감지 우회
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # webdriver 속성 제거
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })
        
        return driver
    
    def login_naver(self) -> bool:
        """네이버 로그인"""
        if not self.naver_id or not self.naver_pw:
            print("⚠️  로그인 정보가 없습니다. 로그인 없이 진행합니다.")
            return False
        
        try:
            print("네이버 로그인 시도 중...")
            self.driver.get("https://nid.naver.com/nidlogin.login")
            time.sleep(2)
            
            # JavaScript로 로그인 (캡차 우회 시도)
            script = f"""
                document.getElementById('id').value = '{self.naver_id}';
                document.getElementById('pw').value = '{self.naver_pw}';
            """
            self.driver.execute_script(script)
            time.sleep(1)
            
            # 로그인 버튼 클릭
            login_btn = self.driver.find_element(By.ID, "log.login")
            login_btn.click()
            
            time.sleep(3)
            
            # 로그인 성공 확인
            if "naver.com" in self.driver.current_url and "nidlogin" not in self.driver.current_url:
                print("✓ 로그인 성공!")
                return True
            else:
                print("⚠️  로그인 실패 (캡차 또는 보안 검증 필요)")
                print("   브라우저 창에서 수동으로 로그인을 완료해주세요.")
                print("   로그인 후 Enter를 누르세요...")
                input()
                return True
                
        except Exception as e:
            print(f"로그인 중 오류: {e}")
            print("로그인 없이 진행합니다...")
            return False
    
    def collect_reviews(self, max_reviews: int = None, rating: int = None, max_rating: int = None) -> List[Dict]:
        """리뷰 수집"""
        # 로그인 시도
        if self.naver_id and self.naver_pw:
            self.login_naver()
            time.sleep(2)
        
        print(f"페이지 로딩: {self.product_url}")
        self.driver.get(self.product_url)
        time.sleep(5)
        
        # 페이지 제목 확인
        page_title = self.driver.title
        print(f"페이지 제목: {page_title}")
        
        if "에러" in page_title or "오류" in page_title:
            print("❌ 페이지 접근 실패")
            print("   로그인이 필요하거나 상품이 존재하지 않습니다.")
            return []
        
        try:
            # 리뷰 탭으로 이동
            self._navigate_to_review_tab()
            
            # 리뷰 더보기 클릭
            self._load_all_reviews(max_reviews)
            
            # 리뷰 파싱
            reviews = self._parse_reviews()
            
            # 별점 필터링
            if rating is not None or max_rating is not None:
                filtered = []
                for r in reviews:
                    r_rating = r.get('rating', 0)
                    
                    if rating is not None and r_rating != rating:
                        continue
                    
                    if max_rating is not None and r_rating > max_rating:
                        continue
                    
                    filtered.append(r)
                
                if rating is not None and max_rating is not None:
                    print(f"별점 {rating}점 이하 {max_rating}점까지 필터링: {len(filtered)}개")
                elif rating is not None:
                    print(f"별점 {rating}점만 필터링: {len(filtered)}개")
                elif max_rating is not None:
                    print(f"별점 {max_rating}점 이하 필터링: {len(filtered)}개")
                
                reviews = filtered
            
            # 수량 제한
            if max_reviews and len(reviews) > max_reviews:
                reviews = reviews[:max_reviews]
                print(f"최대 {max_reviews}개로 제한")
            
            print(f"\n총 {len(reviews)}개의 리뷰를 수집했습니다.")
            return reviews
            
        except Exception as e:
            print(f"리뷰 수집 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            self.driver.quit()
    
    def _navigate_to_review_tab(self):
        """리뷰 탭 클릭"""
        try:
            review_tab_selectors = [
                "//a[contains(text(), '리뷰')]",
                "//a[@href='#REVIEW']",
                "//*[@id='REVIEW']",
                "//button[contains(text(), '리뷰')]",
            ]
            
            for selector in review_tab_selectors:
                try:
                    element = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    element.click()
                    print("리뷰 탭 클릭")
                    time.sleep(2)
                    return
                except:
                    continue
            
            print("⚠️  리뷰 탭을 찾을 수 없습니다. 현재 페이지에서 리뷰를 찾습니다.")
        except Exception as e:
            print(f"리뷰 탭 이동 실패: {e}")
    
    def _load_all_reviews(self, max_reviews: int = None):
        """더보기 버튼 클릭"""
        retry_count = 0
        max_retries = 3
        
        while True:
            try:
                more_buttons = [
                    "//button[contains(text(), '더보기')]",
                    "//a[contains(text(), '더보기')]",
                ]
                
                button_found = False
                for selector in more_buttons:
                    try:
                        button = self.driver.find_element(By.XPATH, selector)
                        if button.is_displayed():
                            button.click()
                            button_found = True
                            print(".", end="", flush=True)
                            time.sleep(1)
                            retry_count = 0
                            break
                    except:
                        continue
                
                if not button_found:
                    retry_count += 1
                    if retry_count >= max_retries:
                        print("\n더 이상 로드할 리뷰가 없습니다.")
                        break
                    time.sleep(1)
                    
            except Exception as e:
                print(f"\n더보기 클릭 중 오류: {e}")
                break
    
    def _parse_reviews(self) -> List[Dict]:
        """페이지에서 리뷰 파싱"""
        reviews = []
        
        # 다양한 선택자 시도 (smartstore와 brand 모두 지원)
        review_selectors = [
            ".HTT4L8U0CU li.PxsZltB5tV",  # brand
            ".RR2FSL9wTc > li",  # brand 대체
            "li._1hZ8W",  # smartstore
            ".reviewItems > li",  # smartstore 대체
        ]
        
        review_elements = []
        for selector in review_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements and len(elements) > 0:
                    review_elements = elements
                    print(f"\n리뷰 요소 발견: {len(elements)}개 (선택자: {selector})")
                    break
            except:
                continue
        
        if not review_elements:
            print("⚠️  리뷰 요소를 찾을 수 없습니다.")
            return []
        
        for idx, element in enumerate(review_elements, 1):
            try:
                review = self._parse_review_element(element)
                if review and review.get('content') and len(review['content']) > 5:
                    reviews.append(review)
                    if idx % 10 == 0:
                        print(f"\r파싱 중: {idx}/{len(review_elements)}", end="", flush=True)
            except Exception as e:
                continue
        
        return reviews
    
    def _parse_review_element(self, element) -> Dict:
        """개별 리뷰 요소 파싱"""
        review = {}
        
        try:
            # 별점 (여러 선택자 시도)
            try:
                rating_selectors = [".n6zq2yy0KA", "em._15NU42", ".star em"]
                for selector in rating_selectors:
                    try:
                        rating_elem = element.find_element(By.CSS_SELECTOR, selector)
                        if rating_elem.text.isdigit():
                            review['rating'] = int(rating_elem.text)
                            break
                    except:
                        continue
                if 'rating' not in review:
                    review['rating'] = None
            except:
                review['rating'] = None
            
            # 리뷰 내용 (여러 선택자 시도)
            try:
                content_selectors = [
                    "span.MX91DFZo2F",  # brand
                    "div._3QDEp",  # smartstore
                    ".KqJ8Qqw082",  # 대체
                ]
                
                contents = []
                for selector in content_selectors:
                    try:
                        content_elements = element.find_elements(By.CSS_SELECTOR, selector)
                        for elem in content_elements:
                            text = elem.text.strip()
                            if text and len(text) > 5:
                                contents.append(text)
                    except:
                        continue
                
                if contents:
                    review['content'] = max(contents, key=len)
                else:
                    review['content'] = None
            except:
                review['content'] = None
            
            # 작성일
            try:
                dates = element.find_elements(By.CSS_SELECTOR, "span.MX91DFZo2F, span[class*='date']")
                for date_elem in dates:
                    date_text = date_elem.text.strip()
                    if re.match(r'\d{2}\.\d{2}\.\d{2}\.?', date_text):
                        review['created_at'] = self._parse_date(date_text)
                        break
                
                if 'created_at' not in review:
                    review['created_at'] = None
            except:
                review['created_at'] = None
            
            return review
            
        except Exception as e:
            return None
    
    def _parse_date(self, date_text: str) -> str:
        """날짜 텍스트를 ISO 형식으로 변환"""
        try:
            if re.match(r'\d{2}\.\d{2}\.\d{2}\.?', date_text):
                parts = date_text.replace('.', '').split()
                if parts:
                    date_str = parts[0]
                    year = '20' + date_str[:2]
                    month = date_str[2:4]
                    day = date_str[4:6]
                    
                    now = datetime.now()
                    parsed_date = datetime(int(year), int(month), int(day))
                    
                    if parsed_date.date() == now.date():
                        return now.strftime("%Y-%m-%dT%H:%M:%SZ")
                    else:
                        import random
                        hour = random.randint(9, 23)
                        minute = random.randint(0, 59)
                        second = random.randint(0, 59)
                        return f"{year}-{month}-{day}T{hour:02d}:{minute:02d}:{second:02d}Z"
            
            return datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        except:
            return datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    def convert_to_backend_format(self, reviews: List[Dict]) -> pd.DataFrame:
        """backend/data/review 형식으로 변환"""
        converted = []
        
        for review in reviews:
            content = normalize_text(review.get('content', ''))
            review_id = int(hashlib.md5(content.encode()).hexdigest()[:10], 16)
            
            converted.append({
                'review_id': review_id,
                'rating': review.get('rating'),
                'text': content,
                'created_at': review.get('created_at', datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))
            })
        
        return pd.DataFrame(converted)
    
    def save_reviews(self, reviews: List[Dict], category: str, product_name: str, 
                    output_format: str = 'csv', output_dir: str = 'backend/data/review'):
        """리뷰 저장"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        safe_product_name = re.sub(r'[^\w\-]', '_', product_name)
        safe_category = re.sub(r'[^\w\-]', '_', category)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        filename = f"reviews_smartstore_{safe_category}_{safe_product_name}_{timestamp}"
        
        df = self.convert_to_backend_format(reviews)
        
        file_path = None
        if output_format == 'csv':
            file_path = output_path / f"{filename}.csv"
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            print(f"\n✓ CSV 저장 완료: {file_path}")
        elif output_format == 'json':
            file_path = output_path / f"{filename}.json"
            df.to_json(file_path, orient='records', force_ascii=False, indent=2)
            print(f"\n✓ JSON 저장 완료: {file_path}")
        elif output_format == 'both':
            csv_path = output_path / f"{filename}.csv"
            json_path = output_path / f"{filename}.json"
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            df.to_json(json_path, orient='records', force_ascii=False, indent=2)
            print(f"\n✓ CSV 저장 완료: {csv_path}")
            print(f"✓ JSON 저장 완료: {json_path}")
            file_path = csv_path
        
        return file_path


def main():
    parser = argparse.ArgumentParser(
        description='네이버 스마트스토어 리뷰 수집 (로그인 지원)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('url', help='스마트스토어 상품 URL')
    parser.add_argument('--category', '-c', required=True, help='카테고리명')
    parser.add_argument('--product-name', '-p', required=True, help='상품명')
    parser.add_argument('--max-reviews', '-m', type=int, default=100, help='최대 리뷰 수')
    parser.add_argument('--rating', '-r', type=int, choices=[1, 2, 3, 4, 5], default=None, help='수집할 별점')
    parser.add_argument('--max-rating', type=int, choices=[1, 2, 3, 4, 5], default=None, help='최대 별점')
    parser.add_argument('--format', '-f', choices=['csv', 'json', 'both'], default='csv', help='출력 형식')
    parser.add_argument('--output-dir', '-o', default='backend/data/review', help='출력 디렉토리')
    parser.add_argument('--naver-id', help='네이버 아이디 (로그인 필요시)')
    parser.add_argument('--naver-pw', help='네이버 비밀번호 (로그인 필요시)')
    parser.add_argument('--headless', action='store_true', help='헤드리스 모드 (로그인 시 비권장)')
    
    args = parser.parse_args()
    
    # 비밀번호 입력 (인자로 안 넘어온 경우)
    naver_id = args.naver_id
    naver_pw = args.naver_pw
    
    if naver_id and not naver_pw:
        naver_pw = getpass.getpass("네이버 비밀번호를 입력하세요: ")
    
    print(f"{'='*60}")
    print(f"네이버 스마트스토어 리뷰 수집 (로그인 지원)")
    print(f"{'='*60}\n")
    print(f"카테고리: {args.category}")
    print(f"상품명: {args.product_name}")
    print(f"최대 리뷰 수: {args.max_reviews}")
    if args.rating:
        print(f"수집 별점: {args.rating}점")
    if args.max_rating:
        print(f"최대 별점: {args.max_rating}점 이하")
    print(f"출력 형식: {args.format}")
    if naver_id:
        print(f"로그인 ID: {naver_id}")
    print()
    
    # 리뷰 수집
    collector = SmartStoreReviewCollectorWithLogin(
        args.url, 
        naver_id=naver_id, 
        naver_pw=naver_pw,
        headless=args.headless
    )
    reviews = collector.collect_reviews(
        max_reviews=args.max_reviews,
        rating=args.rating,
        max_rating=args.max_rating
    )
    
    if not reviews:
        print("\n수집된 리뷰가 없습니다.")
        return
    
    # 저장
    file_path = collector.save_reviews(
        reviews=reviews,
        category=args.category,
        product_name=args.product_name,
        output_format=args.format,
        output_dir=args.output_dir
    )
    
    print(f"\n{'='*60}")
    print(f"✓ 완료! 총 {len(reviews)}개의 리뷰를 수집했습니다.")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
