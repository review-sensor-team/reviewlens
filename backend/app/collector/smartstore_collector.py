"""네이버 스마트스토어 리뷰 수집 모듈"""
import re
import time
import hashlib
from typing import List, Dict, Optional
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
    
    try:
        import undetected_chromedriver as uc
        UC_AVAILABLE = True
    except ImportError:
        UC_AVAILABLE = False
        
except ImportError:
    SELENIUM_AVAILABLE = False
    UC_AVAILABLE = False


def normalize_text(text: str) -> str:
    """텍스트 정규화"""
    if not text:
        return ""
    
    text = text.replace('\n', ' ').replace('\r', ' ')
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
    
    return text


class SmartStoreCollector:
    """네이버 스마트스토어 리뷰 수집"""
    
    def __init__(self, product_url: str, headless: bool = True):
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium과 webdriver-manager가 필요합니다: pip install selenium webdriver-manager")
        
        self.product_url = product_url
        self.product_id = self._extract_product_id(product_url)
        self.driver = None
        self.headless = headless
        
    def _extract_product_id(self, url: str) -> str:
        """URL에서 상품 ID 추출"""
        match = re.search(r'/products/(\d+)', url)
        if not match:
            raise ValueError(f"상품 ID를 찾을 수 없습니다: {url}")
        return match.group(1)
    
    def _init_driver(self):
        """Chrome 드라이버 초기화"""
        if self.driver:
            return
            
        is_brand_naver = 'brand.naver.com' in self.product_url
        
        if is_brand_naver:
            self.driver = self._init_selenium_driver(self.headless)
        else:
            if UC_AVAILABLE:
                self.driver = self._init_uc_driver()
            else:
                self.driver = self._init_selenium_driver(self.headless)
    
    def _init_selenium_driver(self, headless: bool):
        """일반 Selenium WebDriver 초기화"""
        options = Options()
        
        if headless:
            options.add_argument('--headless=new')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-gpu')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })
        
        if not headless:
            try:
                driver.set_window_size(1920, 1080)
            except:
                pass
        
        return driver
    
    def _init_uc_driver(self):
        """undetected-chromedriver 초기화"""
        options = uc.ChromeOptions()
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = uc.Chrome(options=options)
        
        try:
            driver.set_window_size(1920, 1080)
        except:
            pass
        
        return driver
    
    def collect_reviews(self, max_reviews: int = 100, sort_by_low_rating: bool = True) -> List[Dict]:
        """
        리뷰 수집
        
        Args:
            max_reviews: 최대 리뷰 수
            sort_by_low_rating: 별점 낮은순 정렬 여부
            
        Returns:
            리뷰 목록
        """
        try:
            self._init_driver()
            
            print(f"페이지 로딩: {self.product_url}")
            self.driver.get(self.product_url)
            time.sleep(3)
            
            # 리뷰 탭으로 이동
            self._navigate_to_review_tab()
            
            # 별점 낮은순 정렬
            if sort_by_low_rating:
                self._set_sort_by_low_rating()
            
            # 리뷰 수집
            print(f"\n리뷰 수집 중... (최대 {max_reviews}건)")
            reviews = self._collect_reviews_from_pages(max_reviews)
            
            print(f"\n✓ 총 {len(reviews)}개의 리뷰를 수집했습니다.")
            return reviews
            
        except Exception as e:
            print(f"❌ 리뷰 수집 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    def _navigate_to_review_tab(self):
        """리뷰 탭 클릭"""
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(2)
            
            review_tab_selectors = [
                "//a[contains(text(), '리뷰') and not(contains(text(), '이벤트'))]",
                "//button[contains(text(), '리뷰') and not(contains(text(), '이벤트'))]",
                "//a[@href='#REVIEW']",
                "//*[@id='REVIEW']",
                "//li[contains(@class, 'tab')]//a[contains(text(), '리뷰')]",
            ]
            
            for selector in review_tab_selectors:
                try:
                    element = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    time.sleep(1)
                    element.click()
                    print(f"✓ 리뷰 탭 클릭 성공")
                    time.sleep(3)
                    return
                except:
                    continue
            
            print("⚠️  리뷰 탭을 찾을 수 없습니다. 현재 페이지에서 리뷰를 찾습니다.")
            
        except Exception as e:
            print(f"리뷰 탭 이동 실패: {e}")
    
    def _set_sort_by_low_rating(self):
        """리뷰 정렬을 '평점 낮은순'으로 변경"""
        try:
            # 먼저 정렬 버튼/드롭다운 찾기
            sort_selectors = [
                "//button[contains(text(), '정렬')]",
                "//button[contains(@class, 'sort')]",
                "//button[contains(@class, 'Sort')]",
                "//select[contains(@class, 'sort')]",
                "//select[contains(@class, 'Sort')]",
                "//div[contains(@class, 'sort')]//button",
                "//div[contains(@class, 'Sort')]//button",
                "//*[contains(text(), '추천순')]",  # 기본 정렬 옵션
            ]
            
            for selector in sort_selectors:
                try:
                    sort_element = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", sort_element)
                    time.sleep(0.5)
                    sort_element.click()
                    time.sleep(1)
                    
                    # '평점 낮은순' 옵션 찾기 - React 앱을 위한 패턴 추가
                    low_rating_selectors = [
                        # href="#" 형태의 React 링크
                        "//a[@href='#'][contains(text(), '평점 낮은순')]",
                        "//a[@href='#'][contains(text(), '평점낮은순')]",
                        "//a[@href='#']//span[contains(text(), '평점 낮은순')]",
                        "//a[@href='#']//span[contains(text(), '평점낮은순')]",
                        # 일반 패턴
                        "//button[contains(text(), '평점 낮은순')]",
                        "//button[contains(text(), '평점낮은순')]",
                        "//a[contains(text(), '평점 낮은순')]",
                        "//a[contains(text(), '평점낮은순')]",
                        "//li[contains(text(), '평점 낮은순')]",
                        "//li[contains(text(), '평점낮은순')]",
                        "//li//a[contains(text(), '평점 낮은순')]",
                        "//li//a[contains(text(), '평점낮은순')]",
                        "//option[contains(text(), '평점 낮은순')]",
                        "//option[contains(text(), '평점낮은순')]",
                        "//span[contains(text(), '평점 낮은순')]",
                        "//div[contains(text(), '평점 낮은순')]",
                        "//*[text()='평점 낮은순']",
                        "//*[text()='평점낮은순']",
                        "//button[contains(@data-value, 'LOW')]",
                        "//button[contains(@data-sort, 'rating_asc')]",
                    ]
                    
                    for low_selector in low_rating_selectors:
                        try:
                            low_rating_option = self.driver.find_element(By.XPATH, low_selector)
                            if low_rating_option.is_displayed():
                                # React 앱을 위해 JavaScript click 사용
                                self.driver.execute_script("arguments[0].click();", low_rating_option)
                                print(f"✓ 정렬을 '평점 낮은순'으로 변경했습니다. (선택자: {low_selector})")
                                time.sleep(2)
                                return True
                        except Exception as e:
                            continue
                    
                except:
                    continue
            
            # 정렬 옵션을 찾지 못한 경우 페이지 소스에서 확인 및 모든 요소 디버깅
            try:
                page_source = self.driver.page_source
                if '평점 낮은순' in page_source or '평점낮은순' in page_source:
                    print("⚠️  '평점 낮은순' 텍스트는 존재하지만 클릭 가능한 요소를 찾지 못했습니다.")
                    
                    # 모든 '평점 낮은순' 포함 요소 찾기
                    try:
                        all_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '평점') and contains(text(), '낮은순')]")
                        print(f"📍 '평점 낮은순' 포함 요소 {len(all_elements)}개 발견:")
                        for idx, elem in enumerate(all_elements[:5]):  # 최대 5개만
                            try:
                                print(f"  [{idx+1}] 태그: {elem.tag_name}, 표시여부: {elem.is_displayed()}, "
                                      f"활성화: {elem.is_enabled()}, 텍스트: {elem.text[:50] if elem.text else ''}")
                                print(f"      HTML: {elem.get_attribute('outerHTML')[:200]}")
                                
                                # 각 요소에 대해 클릭 시도
                                if elem.is_displayed():
                                    try:
                                        # 방법 1: 일반 클릭
                                        elem.click()
                                        print(f"  ✓ 요소 [{idx+1}] 클릭 성공 (일반 클릭)")
                                        time.sleep(2)
                                        return True
                                    except:
                                        try:
                                            # 방법 2: JavaScript 클릭
                                            self.driver.execute_script("arguments[0].click();", elem)
                                            print(f"  ✓ 요소 [{idx+1}] 클릭 성공 (JS 클릭)")
                                            time.sleep(2)
                                            return True
                                        except:
                                            try:
                                                # 방법 3: 부모 요소 클릭
                                                parent = elem.find_element(By.XPATH, "..")
                                                parent.click()
                                                print(f"  ✓ 요소 [{idx+1}] 부모 클릭 성공")
                                                time.sleep(2)
                                                return True
                                            except Exception as e:
                                                print(f"  ✗ 요소 [{idx+1}] 클릭 실패: {str(e)[:100]}")
                            except Exception as e:
                                print(f"  ✗ 요소 [{idx+1}] 처리 중 오류: {str(e)[:100]}")
                    except Exception as e:
                        print(f"⚠️  요소 검색 중 오류: {str(e)}")
                else:
                    print("⚠️  '평점 낮은순' 정렬 옵션이 페이지에 없습니다.")
            except:
                pass
            
            print("⚠️  '평점 낮은순' 정렬 옵션을 찾을 수 없습니다. 기본 정렬로 진행합니다.")
            return False
            
        except Exception as e:
            print(f"⚠️  정렬 변경 실패: {e}")
            return False
    
    def _collect_reviews_from_pages(self, max_reviews: int = None) -> List[Dict]:
        """여러 페이지를 순회하며 리뷰 수집"""
        all_reviews = []
        visited_pages = set()
        current_page_num = 1
        
        while True:
            page_reviews = self._parse_current_page_reviews()
            
            if page_reviews:
                all_reviews.extend(page_reviews)
                print(f"\r페이지 {current_page_num}: +{len(page_reviews)}개 (총 {len(all_reviews)}개)", end="", flush=True)
            
            if max_reviews and len(all_reviews) >= max_reviews:
                print(f"\n✓ 목표 리뷰 수({max_reviews})에 도달했습니다.")
                return all_reviews[:max_reviews]
            
            if not self._goto_next_page(visited_pages):
                print(f"\n✓ 모든 페이지 수집 완료 (총 {len(all_reviews)}개)")
                break
            
            current_page_num += 1
            time.sleep(2)
        
        return all_reviews
    
    def _parse_current_page_reviews(self) -> List[Dict]:
        """현재 페이지의 리뷰만 파싱"""
        reviews = []
        
        review_selectors = [
            ".HTT4L8U0CU li.PxsZltB5tV",
            ".RR2FSL9wTc > li",
            "ul[class*='review'] > li",
        ]
        
        review_elements = []
        for selector in review_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements and len(elements) > 0:
                    review_elements = elements
                    break
            except:
                continue
        
        for element in review_elements:
            try:
                review = self._parse_review_element(element)
                if review and review.get('content') and len(review['content']) > 5:
                    reviews.append(review)
            except:
                continue
        
        return reviews
    
    def _goto_next_page(self, visited_pages: set) -> bool:
        """다음 페이지로 이동"""
        try:
            try:
                current_page_elem = self.driver.find_element(
                    By.CSS_SELECTOR, 
                    "a[role='menuitem'][aria-current='true']"
                )
                current_page = current_page_elem.text.strip()
                visited_pages.add(current_page)
            except:
                pass
            
            pagination_selectors = [
                "div[role='menubar']",
                "div.w2_v0Jq7tg",
                "div[data-shp-area-id='pgn']",
            ]
            
            pagination_div = None
            for selector in pagination_selectors:
                try:
                    pagination_div = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not pagination_div:
                return False
            
            page_link_selectors = [
                "a.F0MhmLrV2F[aria-current='false']",
                "a[role='menuitem'][aria-current='false']",
            ]
            
            page_links = []
            for selector in page_link_selectors:
                page_links = pagination_div.find_elements(By.CSS_SELECTOR, selector)
                if page_links:
                    break
            
            if page_links:
                for link in page_links:
                    page_num = link.text.strip()
                    if page_num.isdigit() and page_num not in visited_pages:
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", link)
                        time.sleep(0.3)
                        self.driver.execute_script("arguments[0].click();", link)
                        return True
            
            next_button_selectors = [
                "//a[contains(text(), '다음') and @aria-hidden='false']",
                "//a[contains(@class, 'jFLfdWHAWX') and not(@aria-hidden='true')]",
            ]
            
            for selector in next_button_selectors:
                try:
                    button = self.driver.find_element(By.XPATH, selector)
                    if button.is_displayed():
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                        time.sleep(0.3)
                        self.driver.execute_script("arguments[0].click();", button)
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            return False
    
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
            
            # 리뷰 내용
            try:
                content_elements = element.find_elements(By.CSS_SELECTOR, "span.MX91DFZo2F")
                contents = [elem.text.strip() for elem in content_elements if elem.text.strip()]
                if contents:
                    review['content'] = max(contents, key=len)
                else:
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
    
    def convert_to_backend_format(self, reviews: List[Dict]) -> List[Dict]:
        """backend API 형식으로 변환"""
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
        
        return converted
