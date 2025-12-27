#!/usr/bin/env python3
"""
네이버 스마트스토어 리뷰 수집 및 변환 스크립트

수집한 리뷰를 backend/data/review 형식으로 변환하여 저장합니다.

사용법:
    python scripts/collect_smartstore_reviews.py <product_url> [옵션]

예시:
    python scripts/collect_smartstore_reviews.py "https://brand.naver.com/airmade/products/11129902190" \\
        --category appliance_heated_humidifier \\
        --product-name "airmade_4502" \\
        --max-reviews 100 \\
        --min-rating 3 \\
        --format csv

    python scripts/collect_smartstore_reviews.py "https://brand.naver.com/airmade/products/11129902190" \\
        --category appliance_heated_humidifier \\
        --product-name "airmade_4502" \\
        --max-reviews 50 \\
        --format json
"""

import argparse
import json
import re
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import hashlib

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

import pandas as pd


def normalize_text(text: str) -> str:
    """텍스트 정규화 - CSV/JSON 포맷 안전성 확보"""
    if not text:
        return ""
    
    # 줄바꿈을 공백으로 변환
    text = text.replace('\n', ' ').replace('\r', ' ')
    
    # 연속된 공백을 하나로
    text = re.sub(r'\s+', ' ', text)
    
    # 앞뒤 공백 제거
    text = text.strip()
    
    # 제어 문자 제거
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
    
    # 특수 유니코드 문자 정리 (옵션)
    # text = re.sub(r'[^\w\s가-힣ㄱ-ㅎㅏ-ㅣ.,!?~\-/()]+', ' ', text)
    
    return text


class SmartStoreReviewCollector:
    """네이버 스마트스토어 리뷰 수집 및 변환"""
    
    def __init__(self, product_url: str, headless: bool = True):
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium이 설치되어 있지 않습니다. pip install selenium webdriver-manager")
        
        self.product_url = product_url
        self.product_id = self._extract_product_id(product_url)
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
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    
    def collect_reviews(self, max_reviews: int = None, rating: int = None, max_rating: int = None) -> List[Dict]:
        """리뷰 수집"""
        print(f"페이지 로딩: {self.product_url}")
        self.driver.get(self.product_url)
        time.sleep(3)
        
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
                    
                    # rating이 지정된 경우: 해당 별점만
                    if rating is not None and r_rating != rating:
                        continue
                    
                    # max_rating이 지정된 경우: 해당 별점 이하만
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
                            
                            # 현재 로드된 리뷰 수 확인
                            current_count = len(self.driver.find_elements(By.CSS_SELECTOR, ".HTT4L8U0CU li.PxsZltB5tV"))
                            
                            if max_reviews and current_count >= max_reviews:
                                print(f"\n최대 리뷰 수({max_reviews})에 도달했습니다.")
                                return
                            
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
        
        review_selectors = [
            ".HTT4L8U0CU li.PxsZltB5tV",
            ".RR2FSL9wTc > li",
        ]
        
        review_elements = []
        for selector in review_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements and len(elements) > 5:
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
            # 별점
            try:
                rating_elem = element.find_element(By.CSS_SELECTOR, ".n6zq2yy0KA")
                review['rating'] = int(rating_elem.text) if rating_elem.text.isdigit() else None
            except:
                review['rating'] = None
            
            # 리뷰 내용 - 여러 선택자 시도
            try:
                # 전체 텍스트 가져오기
                all_text = element.text
                
                # MX91DFZo2F 클래스의 모든 span 찾기
                content_elements = element.find_elements(By.CSS_SELECTOR, "span.MX91DFZo2F")
                
                # 실제 리뷰 내용은 보통 가장 긴 텍스트
                contents = [elem.text.strip() for elem in content_elements if elem.text.strip()]
                if contents:
                    # 가장 긴 텍스트를 리뷰 내용으로 사용
                    review['content'] = max(contents, key=len)
                else:
                    # 대체: KqJ8Qqw082 클래스 시도
                    try:
                        content_elem = element.find_element(By.CSS_SELECTOR, ".KqJ8Qqw082")
                        review['content'] = content_elem.text.strip()
                    except:
                        review['content'] = None
            except:
                review['content'] = None
            
            # 작성자
            try:
                author_elem = element.find_element(By.CSS_SELECTOR, "strong.MX91DFZo2F")
                review['author'] = author_elem.text.strip()
            except:
                review['author'] = None
            
            # 작성일
            try:
                dates = element.find_elements(By.CSS_SELECTOR, "span.MX91DFZo2F")
                # 날짜 형식 찾기 (YY.MM.DD)
                for date_elem in dates:
                    date_text = date_elem.text.strip()
                    if re.match(r'\d{2}\.\d{2}\.\d{2}\.?', date_text):
                        review['created_at'] = self._parse_date(date_text)
                        break
                
                if 'created_at' not in review:
                    review['created_at'] = None
            except:
                review['created_at'] = None
            
            # 상품 옵션
            try:
                option_elem = element.find_element(By.CSS_SELECTOR, ".b_caIle8kC")
                review['product_option'] = option_elem.text.strip()
            except:
                review['product_option'] = None
            
            return review
            
        except Exception as e:
            return None
    
    def _parse_date(self, date_text: str) -> str:
        """날짜 텍스트를 ISO 형식으로 변환"""
        try:
            # "25.12.17." 형식
            if re.match(r'\d{2}\.\d{2}\.\d{2}\.?', date_text):
                parts = date_text.replace('.', '').split()
                if parts:
                    date_str = parts[0]
                    year = '20' + date_str[:2]
                    month = date_str[2:4]
                    day = date_str[4:6]
                    
                    # 당일 리뷰인 경우 현재 시분초 사용, 아니면 자정으로
                    now = datetime.now()
                    parsed_date = datetime(int(year), int(month), int(day))
                    
                    if parsed_date.date() == now.date():
                        # 당일 리뷰는 현재 시분초 사용
                        return now.strftime("%Y-%m-%dT%H:%M:%SZ")
                    else:
                        # 과거 리뷰는 해당 날짜의 랜덤 시간 생성 (9시-23시 사이)
                        import random
                        hour = random.randint(9, 23)
                        minute = random.randint(0, 59)
                        second = random.randint(0, 59)
                        return f"{year}-{month}-{day}T{hour:02d}:{minute:02d}:{second:02d}Z"
            
            # 기본값
            return datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        except:
            return datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    def convert_to_backend_format(self, reviews: List[Dict]) -> pd.DataFrame:
        """backend/data/review 형식으로 변환"""
        converted = []
        
        for review in reviews:
            # 텍스트 정규화
            content = normalize_text(review.get('content', ''))
            
            # review_id 생성 (content 해시 기반)
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
        # 출력 디렉토리 생성
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 파일명 생성
        safe_product_name = re.sub(r'[^\w\-]', '_', product_name)
        safe_category = re.sub(r'[^\w\-]', '_', category)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        filename = f"reviews_smartstore_{safe_category}_{safe_product_name}_{timestamp}"
        
        # 변환
        df = self.convert_to_backend_format(reviews)
        
        # 저장
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
            file_path = csv_path  # both일 때는 CSV 경로 반환
        
        return file_path


def main():
    parser = argparse.ArgumentParser(
        description='네이버 스마트스토어 리뷰 수집 및 변환',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('url', help='스마트스토어 상품 URL')
    
    parser.add_argument(
        '--category', '-c',
        required=True,
        help='카테고리명 (예: appliance_heated_humidifier)'
    )
    
    parser.add_argument(
        '--product-name', '-p',
        required=True,
        help='상품명 (예: airmade_4502)'
    )
    
    parser.add_argument(
        '--max-reviews', '-m',
        type=int,
        default=100,
        help='최대 리뷰 수 (기본값: 100)'
    )
    
    parser.add_argument(
        '--rating', '-r',
        type=int,
        choices=[1, 2, 3, 4, 5],
        default=None,
        help='수집할 별점 (1-5, 미지정시 모든 별점)'
    )
    
    parser.add_argument(
        '--max-rating',
        type=int,
        choices=[1, 2, 3, 4, 5],
        default=None,
        help='최대 별점 (해당 별점 이하만 수집, 1-5)'
    )
    
    parser.add_argument(
        '--format', '-f',
        choices=['csv', 'json', 'both'],
        default='csv',
        help='출력 형식 (기본값: csv)'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        default='backend/data/review',
        help='출력 디렉토리 (기본값: backend/data/review)'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='헤드리스 모드로 실행'
    )
    
    args = parser.parse_args()
    
    # Selenium 설치 확인
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, NoSuchElementException
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError:
        print("❌ Selenium이 설치되어 있지 않습니다.")
        print("\n설치 방법:")
        print("  pip install selenium webdriver-manager")
        return
    
    print(f"{'='*60}")
    print(f"네이버 스마트스토어 리뷰 수집")
    print(f"{'='*60}\n")
    print(f"카테고리: {args.category}")
    print(f"상품명: {args.product_name}")
    print(f"최대 리뷰 수: {args.max_reviews}")
    if args.rating:
        print(f"수집 별점: {args.rating}점")
    if args.max_rating:
        print(f"최대 별점: {args.max_rating}점 이하")
    print(f"출력 형식: {args.format}")
    print(f"출력 디렉토리: {args.output_dir}\n")
    
    # 리뷰 수집
    collector = SmartStoreReviewCollector(args.url, headless=args.headless)
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
