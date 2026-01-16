"""네이버 스마트스토어 리뷰 수집 모듈"""
import logging
import re
import time
import hashlib
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger("collector.smartstore")

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
        
        logger.info(f"[SmartStoreCollector 초기화] url={product_url}, headless={headless}")
        self.product_url = product_url
        self.product_id = self._extract_product_id(product_url)
        logger.debug(f"  - product_id={self.product_id}")
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
        
        logger.debug("[드라이버 초기화 시작]")
        is_brand_naver = 'brand.naver.com' in self.product_url
        
        # brand.naver.com은 봇 탐지가 강해서 undetected-chromedriver 필수
        if is_brand_naver:
            if UC_AVAILABLE:
                logger.debug("  - brand.naver.com 감지, undetected-chromedriver 사용")
                self.driver = self._init_uc_driver()
            else:
                logger.warning("  - undetected-chromedriver 미설치, Selenium 사용 (봇 탐지 위험)")
                self.driver = self._init_selenium_driver(self.headless)
        else:
            logger.debug("  - Selenium 드라이버 사용")
            self.driver = self._init_selenium_driver(self.headless)
        logger.debug("[드라이버 초기화 완료]")
    
    def _init_selenium_driver(self, headless: bool):
        """일반 Selenium WebDriver 초기화"""
        options = Options()
        
        if headless:
            options.add_argument('--headless=new')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-gpu')
        
        # 기본 옵션
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # 최신 Chrome User-Agent (macOS, 2024년 기준)
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36')
        
        # 추가 봇 탐지 우회 설정
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        options.add_argument('--disable-site-isolation-trials')
        options.add_argument('--lang=ko-KR')
        options.add_argument('--accept-lang=ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7')
        
        # 자동화 흔적 제거
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Preferences 설정
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "webrtc.ip_handling_policy": "disable_non_proxied_udp",
            "webrtc.multiple_routes_enabled": False,
            "webrtc.nonproxied_udp_enabled": False
        }
        options.add_experimental_option("prefs", prefs)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Timeout 설정 (페이지 로드 30초, 스크립트 실행 30초)
        driver.set_page_load_timeout(30)
        driver.set_script_timeout(30)
        
        # JavaScript로 웹드라이버 흔적 제거
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ko-KR', 'ko', 'en-US', 'en']
                });
                window.chrome = {
                    runtime: {}
                };
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
        
        # headless 모드는 uc.Chrome()의 headless 파라미터로만 설정
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        # undetected-chromedriver는 headless 파라미터로 설정
        driver = uc.Chrome(options=options, headless=self.headless, use_subprocess=True)
        
        # Timeout 설정
        driver.set_page_load_timeout(30)
        driver.set_script_timeout(30)
        
        return driver
    
    def collect_reviews(self, max_reviews: int = 100, sort_by_low_rating: bool = True) -> tuple:
        """
        리뷰 수집
        
        Args:
            max_reviews: 최대 리뷰 수
            sort_by_low_rating: 별점 낮은순 정렬 여부
            
        Returns:
            (리뷰 목록, 페이지 제목) 튜플
        """
        logger.info(f"[리뷰 수집 시작] max={max_reviews}, sort_by_low_rating={sort_by_low_rating}")
        page_title = None
        try:
            self._init_driver()
            
            logger.info(f"[페이지 로딩 시작] {self.product_url}")
            print(f"페이지 로딩: {self.product_url}")
            
            try:
                self.driver.get(self.product_url)
                logger.info(f"[페이지 로딩 완료]")
            except Exception as e:
                logger.error(f"[페이지 로딩 실패] {e}")
                raise
            
            time.sleep(3)
            
            # 페이지 제목 가져오기
            try:
                page_title = self.driver.title
                logger.info(f"[페이지 제목 수집] {page_title}")
            except Exception as e:
                logger.warning(f"[페이지 제목 가져오기 실패] {e}")
            
            # 리뷰 탭으로 이동
            self._navigate_to_review_tab()
            
            # 별점 낮은순 정렬
            if sort_by_low_rating:
                self._set_sort_by_low_rating()
            
            # 리뷰 수집
            print(f"\n리뷰 수집 중... (최대 {max_reviews}건)")
            reviews = self._collect_reviews_from_pages(max_reviews)
            
            print(f"\n✓ 총 {len(reviews)}개의 리뷰를 수집했습니다.")
            return reviews, page_title
            
        except Exception as e:
            print(f"❌ 리뷰 수집 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return [], page_title
        finally:
            if self.driver:
                try:
                    # 더 안전한 종료 절차
                    self.driver.close()  # 현재 창 닫기
                    self.driver.quit()   # 드라이버 종료
                except Exception as e:
                    logger.warning(f"[드라이버 종료 중 오류] {e}")
                    try:
                        # 강제 종료 시도
                        self.driver.service.process.kill()
                    except:
                        pass
                finally:
                    self.driver = None
    
    def _navigate_to_review_tab(self):
        """리뷰 탭 클릭"""
        try:
            # 페이지 중간까지 스크롤 (리뷰 탭이 보이도록)
            for i in range(5):
                self.driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(0.8)
            time.sleep(2)
            
            # href="#REVIEW" 링크 찾기
            review_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='#REVIEW']")
            for link in review_links:
                text = link.text.strip()
                # "리뷰"와 "보기" 텍스트가 모두 포함된 링크 찾기
                if "리뷰" in text and "보기" in text:
                    logger.debug(f"  - 리뷰 탭 발견: '{text}'")
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                    time.sleep(1)
                    self.driver.execute_script("arguments[0].click();", link)
                    print(f"✓ 리뷰 탭 클릭 성공")
                    logger.info(f"[리뷰 탭 클릭 성공]")
                    time.sleep(5)  # 리뷰 섹션 로딩 대기
                    return
            
            # 대체 방법: 모든 링크에서 "리뷰" 찾기
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                text = link.text.strip()
                if "리뷰10," in text or ("리뷰" in text and "보기" in text):
                    logger.debug(f"  - 대체 방법으로 리뷰 탭 발견: '{text}'")
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                    time.sleep(1)
                    self.driver.execute_script("arguments[0].click();", link)
                    print(f"✓ 리뷰 탭 클릭 성공")
                    logger.info(f"[리뷰 탭 클릭 성공]")
                    time.sleep(5)
                    return
            
            logger.warning("[리뷰 탭을 찾을 수 없음]")
            print("⚠️  리뷰 탭을 찾을 수 없습니다. 현재 페이지에서 리뷰를 찾습니다.")
            
        except Exception as e:
            logger.error(f"[리뷰 탭 이동 실패] {e}")
            print(f"리뷰 탭 이동 실패: {e}")
    
    def _set_sort_by_low_rating(self):
        """리뷰 정렬을 '평점 낮은순'으로 변경"""
        try:
            logger.debug("[정렬 옵션 찾기 시작]")
            
            # 발견한 정렬 링크 직접 찾기 (class="JBnM4aPJaH")
            sort_links = self.driver.find_elements(By.CSS_SELECTOR, "a.JBnM4aPJaH")
            logger.debug(f"  - a.JBnM4aPJaH 링크 {len(sort_links)}개 발견")
            
            for link in sort_links:
                text = link.text.strip()
                logger.debug(f"    정렬 옵션: '{text}'")
                if "낮은순" in text:
                    logger.info(f"[평점 낮은순 옵션 발견] '{text}'")
                    self.driver.execute_script("arguments[0].click();", link)
                    print(f"✓ 정렬을 '평점 낮은순'으로 변경했습니다.")
                    logger.info(f"[평점 낮은순 정렬 완료]")
                    time.sleep(3)  # 정렬 후 로딩 대기
                    return True
            
            # 대체 방법: 모든 링크에서 "평점 낮은순" 찾기
            logger.debug("  - 대체 방법으로 정렬 옵션 검색")
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                text = link.text.strip()
                if "평점 낮은순" in text or "평점낮은순" in text:
                    logger.info(f"[평점 낮은순 대체 방법으로 발견] '{text}'")
                    self.driver.execute_script("arguments[0].click();", link)
                    print(f"✓ 정렬을 '평점 낮은순'으로 변경했습니다.")
                    logger.info(f"[평점 낮은순 정렬 완료]")
                    time.sleep(3)
                    return True
            
            logger.warning("[평점 낮은순 정렬 옵션을 찾지 못함]")
            print("⚠️  '평점 낮은순' 정렬 옵션을 찾을 수 없습니다. 기본 정렬로 진행합니다.")
            return False
            
        except Exception as e:
            logger.error(f"[정렬 변경 실패] {e}")
            print(f"⚠️  정렬 변경 실패: {e}")
            return False
    
    def _collect_reviews_from_pages(self, max_reviews: int = None) -> List[Dict]:
        """여러 페이지를 순회하며 리뷰 수집"""
        all_reviews = []
        visited_pages = set()
        current_page_num = 1
        
        logger.info(f"[페이지 수집 시작] max_reviews={max_reviews}")
        
        while True:
            logger.debug(f"[페이지 {current_page_num}] 파싱 시작...")
            page_reviews = self._parse_current_page_reviews()
            
            if page_reviews:
                all_reviews.extend(page_reviews)
                print(f"\r페이지 {current_page_num}: +{len(page_reviews)}개 (총 {len(all_reviews)}개)", end="", flush=True)
                logger.info(f"[페이지 {current_page_num}] +{len(page_reviews)}개 수집 (누적: {len(all_reviews)}개)")
            else:
                logger.warning(f"[페이지 {current_page_num}] 리뷰 없음")
            
            if max_reviews and len(all_reviews) >= max_reviews:
                print(f"\n✓ 목표 리뷰 수({max_reviews})에 도달했습니다.")
                logger.info(f"[수집 완료] 목표 도달: {len(all_reviews)}개")
                return all_reviews[:max_reviews]
            
            logger.debug(f"[페이지 {current_page_num}] 다음 페이지로 이동 시도...")
            next_page_found = self._goto_next_page(visited_pages)
            logger.debug(f"[페이지 {current_page_num}] 다음 페이지 존재: {next_page_found}")
            
            if not next_page_found:
                print(f"\n✓ 모든 페이지 수집 완료 (총 {len(all_reviews)}개)")
                logger.info(f"[수집 완료] 더 이상 페이지 없음: {len(all_reviews)}개")
                break
            
            current_page_num += 1
        
        return all_reviews
    
    def _parse_current_page_reviews(self) -> List[Dict]:
        """현재 페이지의 리뷰만 파싱 (스크롤하여 모든 리뷰 로드)"""
        reviews = []
        
        # 발견한 리뷰 아이템 선택자 추가
        review_selectors = [
            "li.V5XROudBPi",  # 2024년 현재 네이버 스마트스토어 리뷰 아이템
            ".HTT4L8U0CU li.PxsZltB5tV",
            ".RR2FSL9wTc > li",
            "ul[class*='review'] > li",
        ]
        
        # 페이지 내에서 스크롤하여 모든 리뷰 로드
        logger.debug("  - 페이지 스크롤 시작 (리뷰 로드)")
        last_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 10
        
        while scroll_attempts < max_scroll_attempts:
            # 현재까지 로드된 리뷰 수 확인
            current_count = 0
            for selector in review_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        current_count = len(elements)
                        break
                except:
                    continue
            
            logger.debug(f"    스크롤 {scroll_attempts + 1}: 리뷰 {current_count}개")
            
            # 리뷰 수가 증가하지 않으면 스크롤 중단
            if current_count > 0 and current_count == last_count:
                logger.debug(f"    → 더 이상 리뷰가 로드되지 않음 (총 {current_count}개)")
                break
            
            last_count = current_count
            
            # 페이지 끝까지 스크롤
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)  # 리뷰 로딩 대기
            
            scroll_attempts += 1
        
        # 최종 리뷰 요소 수집
        review_elements = []
        for selector in review_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements and len(elements) > 0:
                    logger.debug(f"  - 선택자 '{selector}'로 {len(elements)}개 리뷰 발견 (스크롤 완료)")
                    review_elements = elements
                    break
            except:
                continue
        
        if not review_elements:
            logger.warning("[리뷰 요소를 찾을 수 없음]")
        
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
            logger.debug("[다음 페이지 이동] 시작")
            
            # 리뷰 영역으로 스크롤 (다른 탭 페이지네이션 클릭 방지)
            try:
                review_section = self.driver.find_element(By.CSS_SELECTOR, "#REVIEW")
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", review_section)
                time.sleep(0.5)
                logger.debug("  - 리뷰 영역으로 스크롤 완료")
            except Exception as e:
                logger.debug(f"  - 리뷰 영역 스크롤 실패 (무시): {e}")
            
            # 리뷰 영역의 페이지네이션 div 찾기 (다른 탭 제외)
            pagination_selectors = [
                "#REVIEW div[role='menubar']",  # 리뷰 탭 내부의 페이지네이션만
                "#REVIEW div.w2_v0Jq7tg",
                "#REVIEW div[data-shp-area-id='pgn']",
                "section[id*='REVIEW'] div[role='menubar']",
            ]
            
            pagination_div = None
            for selector in pagination_selectors:
                try:
                    pagination_div = self.driver.find_element(By.CSS_SELECTOR, selector)
                    logger.debug(f"  - 리뷰 영역의 페이지네이션 div 발견: {selector}")
                    break
                except:
                    continue
            
            if not pagination_div:
                logger.warning("  ✗ 리뷰 영역의 페이지네이션 div를 찾을 수 없습니다")
                return False
            
            # 현재 페이지 번호 파악 - 리뷰 영역 페이지네이션에서만 찾기
            try:
                all_page_links = pagination_div.find_elements(By.CSS_SELECTOR, "a[role='menuitem']")
                current_page = None
                
                for link in all_page_links:
                    aria_current = link.get_attribute('aria-current')
                    text_content = link.text.strip()
                    
                    # aria-current='true'이면서 숫자인 경우
                    if aria_current == 'true' and text_content.isdigit():
                        current_page = text_content
                        break
                
                # 못 찾으면 다른 방법 시도 - disabled 또는 active 클래스
                if not current_page:
                    for link in all_page_links:
                        text_content = link.text.strip()
                        if text_content.isdigit():
                            class_attr = link.get_attribute('class') or ''
                            if 'active' in class_attr.lower() or 'current' in class_attr.lower():
                                current_page = text_content
                                break
                
                if current_page:
                    visited_pages.add(current_page)
                    logger.debug(f"  - 현재 페이지 확정: {current_page}")
                else:
                    logger.warning(f"  ⚠️  현재 페이지 번호를 찾지 못했습니다")
            except Exception as e:
                logger.debug(f"  - 현재 페이지 번호 감지 실패: {e}")
            
            # 페이지 링크 찾기
            page_link_selectors = [
                "a.F0MhmLrV2F[aria-current='false']",
                "a[role='menuitem'][aria-current='false']",
            ]
            
            page_links = []
            for selector in page_link_selectors:
                page_links = pagination_div.find_elements(By.CSS_SELECTOR, selector)
                if page_links:
                    logger.debug(f"  - 페이지 링크 {len(page_links)}개 발견: {selector}")
                    break
            
            # 방문하지 않은 페이지 링크 클릭
            if page_links:
                for link in page_links:
                    # aria-label과 text 모두 확인
                    aria_label = link.get_attribute('aria-label')
                    text_content = link.text.strip()
                    
                    # 페이지 번호 추출
                    page_num = None
                    if aria_label:
                        import re
                        numbers = re.findall(r'\d+', aria_label)
                        if numbers and len(numbers[0]) <= 3:
                            page_num = numbers[0]
                    
                    if not page_num and text_content.isdigit():
                        page_num = text_content
                    
                    logger.debug(f"  - 링크 확인: aria-label='{aria_label}', text='{text_content}', 추출된 페이지={page_num}, 방문여부: {page_num in visited_pages if page_num else 'Unknown'}")
                    
                    if page_num and page_num not in visited_pages:
                        logger.info(f"  ✓ 페이지 {page_num}로 이동")
                        visited_pages.add(page_num)
                        
                        # 페이지 링크 클릭
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", link)
                        time.sleep(0.5)
                        self.driver.execute_script("arguments[0].click();", link)
                        time.sleep(2)
                        
                        # URL에 #REVIEW 해시 강제 추가 (다른 탭으로 이동 방지)
                        current_url = self.driver.current_url
                        if '#REVIEW' not in current_url:
                            base_url = current_url.split('#')[0]
                            self.driver.get(base_url + '#REVIEW')
                            time.sleep(1.5)
                            logger.debug("  - #REVIEW 해시 추가")
                        
                        # 리뷰 영역으로 다시 스크롤
                        try:
                            review_section = self.driver.find_element(By.CSS_SELECTOR, "#REVIEW")
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'start'});", review_section)
                            time.sleep(0.5)
                        except:
                            pass
                        
                        return True
                logger.debug(f"  - 모든 페이지 링크 방문 완료 (총 {len(page_links)}개)")
            else:
                logger.debug("  - 페이지 링크 없음")
            
            # 다음 버튼 찾기
            logger.debug("  - '다음' 버튼 검색 중...")
            next_button_selectors = [
                "//a[contains(text(), '다음') and @aria-hidden='false']",
                "//a[contains(@class, 'jFLfdWHAWX') and not(@aria-hidden='true')]",
            ]
            
            for selector in next_button_selectors:
                try:
                    button = self.driver.find_element(By.XPATH, selector)
                    if button.is_displayed():
                        logger.info(f"  ✓ '다음' 버튼 클릭: {selector}")
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                        time.sleep(0.3)
                        self.driver.execute_script("arguments[0].click();", button)
                        return True
                except Exception as e:
                    logger.debug(f"  - '다음' 버튼 시도 실패 ({selector}): {str(e)[:100]}")
            
            logger.warning("  ✗ 더 이상 다음 페이지가 없습니다")
            return False
            
        except Exception as e:
            logger.error(f"  ✗ 페이지 이동 중 오류: {e}")
            return False
    
    def _parse_review_element(self, element) -> Dict:
        """개별 리뷰 요소 파싱"""
        review = {}
        
        try:
            # 전체 텍스트 가져오기
            full_text = element.text.strip()
            
            if not full_text or len(full_text) < 10:
                return None
            
            # 별점 찾기
            try:
                # "평점\n5" 또는 "별점 5" 패턴
                rating_match = re.search(r'평점\s*(\d)', full_text)
                if rating_match:
                    rating = int(rating_match.group(1))
                    # 별점 3개 초과는 무시 (임시 주석 - 분포 확인용)
                    # if rating > 3:
                    #     logger.debug(f"  - 별점 {rating}개: 3개 초과로 건너뜀")
                    #     return None
                    review['rating'] = rating
                else:
                    review['rating'] = None
            except:
                review['rating'] = None
            
            # 날짜 찾기 (26.01.14 또는 2026.01.14 형식)
            try:
                date_match = re.search(r'(\d{2,4})\.(\d{2})\.(\d{2})\.?', full_text)
                if date_match:
                    year = date_match.group(1)
                    month = date_match.group(2)
                    day = date_match.group(3)
                    
                    # 2자리 연도를 4자리로 변환
                    if len(year) == 2:
                        year = '20' + year
                    
                    review['created_at'] = f"{year}-{month}-{day}T12:00:00Z"
                    review['review_date'] = f"{year}.{month}.{day}"
                else:
                    review['created_at'] = None
                    review['review_date'] = None
            except:
                review['created_at'] = None
                review['review_date'] = None
            
            # 리뷰 내용 추출 (날짜 이후 텍스트, 판매자 답변 제외)
            try:
                # 날짜 이후의 텍스트를 리뷰 내용으로 간주
                lines = full_text.split('\n')
                content_lines = []
                found_date = False
                in_seller_reply = False
                
                for line in lines:
                    line_stripped = line.strip()
                    
                    # 판매자 답변 시작 감지 ("판매자"로 시작하는 라인)
                    if line_stripped.startswith('판매자'):
                        in_seller_reply = True
                        logger.debug(f"    → 판매자 답변 감지, 이후 내용 제외")
                        break
                    
                    # 날짜 패턴 이후부터 수집
                    if re.search(r'\d{2}\.\d{2}\.\d{2}', line_stripped):
                        found_date = True
                        # 날짜 라인에서 사이즈 정보도 포함될 수 있음
                        parts = line_stripped.split('사이즈:')
                        if len(parts) > 1:
                            review['product_option'] = '사이즈: ' + parts[1].strip()
                        continue
                    
                    if found_date and line_stripped and not in_seller_reply:
                        # "사진/비디오 수", "평점" 등의 메타데이터 제외
                        skip_keywords = ['사진/비디오', '평점', '별점', '도움이 돼요', '신고하기']
                        if not any(skip in line_stripped for skip in skip_keywords):
                            content_lines.append(line_stripped)
                
                if content_lines:
                    review['content'] = ' '.join(content_lines)
                    review['review_text'] = review['content']  # 호환성
                else:
                    # 대체: 전체 텍스트에서 의미있는 부분 추출
                    review['content'] = full_text
                    review['review_text'] = full_text
            except:
                review['content'] = full_text
                review['review_text'] = full_text
            
            # 작성자 ID 찾기 (패턴: slow****, chef******* 등)
            try:
                author_match = re.search(r'([a-z]+\*+)', full_text)
                if author_match:
                    review['author'] = author_match.group(1)
                else:
                    review['author'] = None
            except:
                review['author'] = None
            
            logger.debug(f"  - 리뷰 파싱 성공: rating={review.get('rating')}, date={review.get('review_date')}, content_len={len(review.get('content', ''))}")
            return review
            
        except Exception as e:
            logger.debug(f"  - 리뷰 파싱 실패: {e}")
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
    
    def collect_and_analyze(self, category: str, max_reviews: int = 100, 
                           sort_by_low_rating: bool = True) -> Dict:
        """리뷰 수집부터 Factor 분석까지 전체 파이프라인 실행
        
        Args:
            category: 상품 카테고리 (예: 'appliance_heated_humidifier')
            max_reviews: 최대 수집 리뷰 개수
            sort_by_low_rating: 낮은 평점 순 정렬 여부
            
        Returns:
            {
                'reviews': List[Dict],  # Factor 분석이 포함된 리뷰 리스트
                'page_title': str,      # 페이지 제목
                'total_count': int      # 총 리뷰 개수
            }
        """
        from .factor_analyzer import FactorAnalyzer
        
        logger.info(f"[리뷰 수집 및 분석 시작] category={category}, max_reviews={max_reviews}")
        
        # 1. 리뷰 수집
        reviews, page_title = self.collect_reviews(
            max_reviews=max_reviews,
            sort_by_low_rating=sort_by_low_rating
        )
        logger.info(f"[리뷰 수집 완료] count={len(reviews) if reviews else 0}")
        
        if not reviews:
            logger.warning(f"[리뷰 수집 실패] 수집된 리뷰가 없음")
            return {
                'reviews': [],
                'page_title': page_title,
                'total_count': 0
            }
        
        # 2. backend 형식으로 변환
        converted_reviews = self.convert_to_backend_format(reviews)
        logger.debug(f"[리뷰 변환 완료] count={len(converted_reviews)}")
        
        # 3. 중복 제거 (review_id 기준)
        converted_reviews = self._remove_duplicates(converted_reviews)
        
        # 4. Factor 분석
        analyzer = FactorAnalyzer(category=category)
        logger.debug(f"[Factor 분석 시작] category={category}")
        
        for review in converted_reviews:
            factor_matches = analyzer.analyze_review(review['text'])
            review['factor_matches'] = factor_matches
        
        logger.info(f"[Factor 분석 완료] reviews={len(converted_reviews)}")
        
        return {
            'reviews': converted_reviews,
            'page_title': page_title,
            'total_count': len(converted_reviews)
        }
    
    def _remove_duplicates(self, reviews: List[Dict]) -> List[Dict]:
        """중복 리뷰 제거 (review_id 기준)"""
        seen_ids = set()
        unique_reviews = []
        
        for review in reviews:
            review_id = review['review_id']
            if review_id not in seen_ids:
                seen_ids.add(review_id)
                unique_reviews.append(review)
        
        if len(unique_reviews) < len(reviews):
            logger.info(f"[중복 제거] {len(reviews)}건 → {len(unique_reviews)}건")
        
        return unique_reviews
