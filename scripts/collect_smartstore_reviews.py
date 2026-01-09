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
<<<<<<< HEAD
<<<<<<< HEAD
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import undetected_chromedriver as uc
=======
=======
>>>>>>> dev
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
<<<<<<< HEAD
>>>>>>> dev
=======
>>>>>>> dev
    SELENIUM_AVAILABLE = True
    
    # undetected-chromedriver는 선택적으로 import
    try:
        import undetected_chromedriver as uc
        UC_AVAILABLE = True
    except ImportError:
        UC_AVAILABLE = False
        
except ImportError:
    SELENIUM_AVAILABLE = False
    UC_AVAILABLE = False

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
<<<<<<< HEAD
<<<<<<< HEAD
            raise ImportError("Selenium과 undetected-chromedriver가 설치되어 있지 않습니다. pip install selenium undetected-chromedriver")
=======
            raise ImportError("Selenium과 webdriver-manager가 설치되어 있지 않습니다. pip install selenium webdriver-manager")
>>>>>>> dev
=======
            raise ImportError("Selenium과 webdriver-manager가 설치되어 있지 않습니다. pip install selenium webdriver-manager")
>>>>>>> dev
        
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
<<<<<<< HEAD
<<<<<<< HEAD
        """Chrome 드라이버 초기화 - undetected-chromedriver 사용"""
        options = uc.ChromeOptions()
=======
=======
>>>>>>> dev
        """Chrome 드라이버 초기화 - URL에 따라 다른 드라이버 사용"""
        is_brand_naver = 'brand.naver.com' in self.product_url
        
        if is_brand_naver:
            # brand.naver.com: 일반 Selenium WebDriver 사용 (headless 가능)
            print(f"드라이버: Selenium WebDriver (headless={headless})")
            return self._init_selenium_driver(headless)
        else:
            # 일반 스마트스토어: undetected-chromedriver 사용 (headless 강제 비활성화)
            if not UC_AVAILABLE:
                print("⚠️  undetected-chromedriver가 설치되지 않았습니다.")
                print("   일반 스마트스토어는 undetected-chromedriver 권장: pip install undetected-chromedriver")
                print("   일반 Selenium WebDriver로 시도합니다...")
                return self._init_selenium_driver(headless)
            
            print("드라이버: undetected-chromedriver (headless=False, 봇 감지 회피)")
            return self._init_uc_driver()
    
    def _init_selenium_driver(self, headless: bool):
        """일반 Selenium WebDriver 초기화"""
        options = Options()
<<<<<<< HEAD
>>>>>>> dev
=======
>>>>>>> dev
        
        # headless 모드 설정
        if headless:
            options.add_argument('--headless=new')
            options.add_argument('--window-size=1920,1080')
<<<<<<< HEAD
<<<<<<< HEAD
=======
            options.add_argument('--disable-gpu')
>>>>>>> dev
=======
            options.add_argument('--disable-gpu')
>>>>>>> dev
        
        # 기본 설정
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
<<<<<<< HEAD
<<<<<<< HEAD
        # undetected-chromedriver로 드라이버 생성
        driver = uc.Chrome(options=options)
        
        # 창 크기 설정 (headless가 아닐 때만)
=======
=======
>>>>>>> dev
        # User-Agent 설정 (봇 감지 회피)
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # 자동화 감지 비활성화
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # ChromeDriverManager로 드라이버 생성
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # 자동화 감지 우회
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })
        
        # 창 크기 설정
<<<<<<< HEAD
>>>>>>> dev
=======
>>>>>>> dev
        if not headless:
            try:
                driver.set_window_size(1920, 1080)
            except:
                pass
        
        return driver
    
<<<<<<< HEAD
<<<<<<< HEAD
=======
=======
>>>>>>> dev
    def _init_uc_driver(self):
        """undetected-chromedriver 초기화 (headless 비활성화)"""
        options = uc.ChromeOptions()
        
        # headless는 항상 False (봇 감지 회피)
        options.add_argument('--window-size=1920,1080')
        
        # 기본 설정
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # undetected-chromedriver로 드라이버 생성
        driver = uc.Chrome(options=options)
        
        # 창 크기 설정
        try:
            driver.set_window_size(1920, 1080)
        except:
            pass
        
        return driver
    
<<<<<<< HEAD
>>>>>>> dev
=======
>>>>>>> dev
    def _wait_for_captcha(self):
        """보안확인(CAPTCHA) 페이지 감지 및 대기"""
        max_wait_time = 120  # 최대 2분 대기
        check_interval = 2
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            try:
                page_source = self.driver.page_source.lower()
                page_title = self.driver.title.lower()
                current_url = self.driver.current_url.lower()
                
                # CAPTCHA 페이지 감지
                captcha_indicators = [
                    '보안확인' in page_source or '보안확인' in page_title,
                    'captcha' in page_source or 'captcha' in page_title,
                    '자동입력 방지' in page_source,
                    'security check' in page_source,
                    '/gate' in current_url or 'captcha' in current_url
                ]
                
                if any(captcha_indicators):
                    if elapsed_time == 0:
                        print("\n" + "="*60)
                        print("⚠️  보안확인 페이지가 감지되었습니다.")
                        print("브라우저에서 보안확인 문제를 풀어주세요.")
                        print("문제를 풀면 자동으로 계속 진행됩니다...")
                        print("="*60 + "\n")
                    
                    # 계속 대기
                    time.sleep(check_interval)
                    elapsed_time += check_interval
                    
                    if elapsed_time % 10 == 0:
                        print(f"대기 중... ({elapsed_time}초 경과)")
                else:
                    # CAPTCHA가 없으면 정상 진행
                    if elapsed_time > 0:
                        print("✓ 보안확인 완료! 페이지 로딩 중...")
                        time.sleep(2)  # 페이지 완전 로딩 대기
                    return
                    
            except Exception as e:
                print(f"CAPTCHA 확인 중 오류: {e}")
                return
        
        print("⚠️  보안확인 대기 시간 초과. 계속 진행합니다...")
    
    def collect_reviews(self, max_reviews: int = None, rating: int = None, max_rating: int = None) -> List[Dict]:
        """리뷰 수집"""
        print(f"페이지 로딩: {self.product_url}")
        self.driver.get(self.product_url)
        time.sleep(3)
        
        # CAPTCHA 확인 및 대기
        self._wait_for_captcha()
        
        # 페이지 제목 확인
        page_title = self.driver.title
        print(f"페이지 제목: {page_title}")
        
        # 에러 페이지 체크
        if "에러" in page_title or "오류" in page_title or "존재하지 않습니다" in page_title:
            print("❌ 페이지 접근 실패 - 상품이 존재하지 않거나 접근이 제한됨")
            return []
        
        try:
            # 리뷰 탭으로 이동
            self._navigate_to_review_tab()
            
<<<<<<< HEAD
<<<<<<< HEAD
=======
=======
>>>>>>> dev
            # 별점 필터가 있으면 '평점 낮은순' 정렬로 변경
            if rating is not None or max_rating is not None:
                self._set_sort_by_low_rating()
            
<<<<<<< HEAD
>>>>>>> dev
=======
>>>>>>> dev
            # 여러 페이지에서 리뷰 수집
            print("\n리뷰 데이터 수집 중...")
            reviews = self._collect_reviews_from_pages(max_reviews)
            
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
            # 스크롤을 아래로 내려서 리뷰 섹션 찾기
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(2)
            
            review_tab_selectors = [
                "//a[contains(text(), '리뷰') and not(contains(text(), '이벤트'))]",
                "//button[contains(text(), '리뷰') and not(contains(text(), '이벤트'))]",
                "//a[@href='#REVIEW']",
                "//*[@id='REVIEW']",
                "//li[contains(@class, 'tab')]//a[contains(text(), '리뷰')]",
                "//a[contains(@class, 'tab') and contains(text(), '리뷰')]",
            ]
            
            for selector in review_tab_selectors:
                try:
                    element = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    # 요소가 보이도록 스크롤
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    time.sleep(1)
                    element.click()
                    print(f"✓ 리뷰 탭 클릭 성공 (선택자: {selector[:50]}...)")
                    time.sleep(3)  # 리뷰 로딩 대기
                    
<<<<<<< HEAD
<<<<<<< HEAD
                    # 리뷰 탭 클릭 후 페이지 소스 확인
=======
                    # 리뷰 구조 확인 (디버깅용)
>>>>>>> dev
=======
                    # 리뷰 구조 확인 (디버깅용)
>>>>>>> dev
                    self._debug_review_structure()
                    return
                except:
                    continue
            
            print("⚠️  리뷰 탭을 찾을 수 없습니다. 현재 페이지에서 리뷰를 찾습니다.")
            self._debug_review_structure()
            
        except Exception as e:
            print(f"리뷰 탭 이동 실패: {e}")
    
<<<<<<< HEAD
<<<<<<< HEAD
    def _debug_review_structure(self):
        """리뷰 구조 디버깅"""
        try:
            page_source = self.driver.page_source
            
            # 리뷰 관련 모든 요소 찾기
            print("\n[디버깅] 리뷰 구조 분석:")
            
            # 1. 모든 탭 찾기
            tabs = self.driver.find_elements(By.CSS_SELECTOR, "a, button")
            review_tabs = [tab for tab in tabs if '리뷰' in tab.text and '이벤트' not in tab.text]
            if review_tabs:
                print(f"  - 발견된 리뷰 탭: {len(review_tabs)}개")
                for i, tab in enumerate(review_tabs[:3], 1):
                    print(f"    {i}. 텍스트: '{tab.text}', 태그: {tab.tag_name}, 클래스: {tab.get_attribute('class')}")
            
            # 2. ul, li 구조 찾기
            all_uls = self.driver.find_elements(By.TAG_NAME, "ul")
            print(f"  - 전체 <ul> 요소: {len(all_uls)}개")
            
            for ul in all_uls:
                ul_class = ul.get_attribute('class')
                if ul_class and ('review' in ul_class.lower() or 'comment' in ul_class.lower()):
                    li_count = len(ul.find_elements(By.TAG_NAME, "li"))
                    print(f"    └─ 리뷰 관련 <ul> 클래스: '{ul_class}', <li> 개수: {li_count}")
                    
                    # 첫 번째 li의 구조 확인
                    if li_count > 0:
                        first_li = ul.find_elements(By.TAG_NAME, "li")[0]
                        li_class = first_li.get_attribute('class')
                        li_text_preview = first_li.text[:100] if first_li.text else "(텍스트 없음)"
                        print(f"       첫 번째 <li> 클래스: '{li_class}'")
                        print(f"       텍스트 미리보기: {li_text_preview}...")
            
        except Exception as e:
            print(f"  디버깅 중 오류: {e}")
    
    def _collect_reviews_from_pages(self, max_reviews: int = None) -> List[Dict]:
        """여러 페이지를 순회하며 리뷰 수집"""
        all_reviews = []
        visited_pages = set()
        current_page_num = 1
        
        while True:
            # 현재 페이지의 리뷰 수집
            page_reviews = self._parse_current_page_reviews()
            
            if page_reviews:
                all_reviews.extend(page_reviews)
                print(f"\r페이지 {current_page_num}: +{len(page_reviews)}개 (총 {len(all_reviews)}개)", end="", flush=True)
            
            # 목표 수량 도달 체크
            if max_reviews and len(all_reviews) >= max_reviews:
                print(f"\n✓ 목표 리뷰 수({max_reviews})에 도달했습니다.")
                return all_reviews[:max_reviews]
            
            # 다음 페이지로 이동
            if not self._goto_next_page(visited_pages):
                print(f"\n✓ 모든 페이지 수집 완료 (총 {len(all_reviews)}개)")
                break
            
            current_page_num += 1
            time.sleep(2)
        
        return all_reviews
    
=======
=======
>>>>>>> dev
    def _set_sort_by_low_rating(self):
        """리뷰 정렬을 '평점 낮은순'으로 변경"""
        try:
            # 정렬 버튼/드롭다운 찾기
            sort_selectors = [
                "//button[contains(text(), '정렬')]",
                "//select[contains(@class, 'sort')]",
                "//button[contains(@class, 'sort')]",
                "//a[contains(text(), '정렬')]",
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
                    
                    # '평점 낮은순' 옵션 찾기
                    low_rating_selectors = [
                        "//button[contains(text(), '평점 낮은순')]",
                        "//a[contains(text(), '평점 낮은순')]",
                        "//li[contains(text(), '평점 낮은순')]",
                        "//option[contains(text(), '평점 낮은순')]",
                    ]
                    
                    for low_selector in low_rating_selectors:
                        try:
                            low_rating_option = self.driver.find_element(By.XPATH, low_selector)
                            if low_rating_option.is_displayed():
                                self.driver.execute_script("arguments[0].click();", low_rating_option)
                                print("✓ 정렬을 '평점 낮은순'으로 변경했습니다.")
                                time.sleep(2)  # 정렬 후 리뷰 재로딩 대기
                                return True
                        except:
                            continue
                    
                except:
                    continue
            
            print("⚠️  '평점 낮은순' 정렬 옵션을 찾을 수 없습니다. 기본 정렬로 진행합니다.")
            return False
            
        except Exception as e:
            print(f"⚠️  정렬 변경 실패: {e}")
            return False
    
    def _debug_review_structure(self):
        """리뷰 구조 디버깅"""
        try:
            page_source = self.driver.page_source
            
            # 리뷰 관련 모든 요소 찾기
            print("\n[디버깅] 리뷰 구조 분석:")
            
            # 1. 모든 탭 찾기
            tabs = self.driver.find_elements(By.CSS_SELECTOR, "a, button")
            review_tabs = [tab for tab in tabs if '리뷰' in tab.text and '이벤트' not in tab.text]
            if review_tabs:
                print(f"  - 발견된 리뷰 탭: {len(review_tabs)}개")
                for i, tab in enumerate(review_tabs[:3], 1):
                    print(f"    {i}. 텍스트: '{tab.text}', 태그: {tab.tag_name}, 클래스: {tab.get_attribute('class')}")
            
            # 2. ul, li 구조 찾기
            all_uls = self.driver.find_elements(By.TAG_NAME, "ul")
            print(f"  - 전체 <ul> 요소: {len(all_uls)}개")
            
            for ul in all_uls:
                ul_class = ul.get_attribute('class')
                if ul_class and ('review' in ul_class.lower() or 'comment' in ul_class.lower()):
                    li_count = len(ul.find_elements(By.TAG_NAME, "li"))
                    print(f"    └─ 리뷰 관련 <ul> 클래스: '{ul_class}', <li> 개수: {li_count}")
                    
                    # 첫 번째 li의 구조 확인
                    if li_count > 0:
                        first_li = ul.find_elements(By.TAG_NAME, "li")[0]
                        li_class = first_li.get_attribute('class')
                        li_text_preview = first_li.text[:100] if first_li.text else "(텍스트 없음)"
                        print(f"       첫 번째 <li> 클래스: '{li_class}'")
                        print(f"       텍스트 미리보기: {li_text_preview}...")
            
        except Exception as e:
            print(f"  디버깅 중 오류: {e}")
    
    def _collect_reviews_from_pages(self, max_reviews: int = None) -> List[Dict]:
        """여러 페이지를 순회하며 리뷰 수집"""
        all_reviews = []
        visited_pages = set()
        current_page_num = 1
        
        while True:
            # 현재 페이지의 리뷰 수집
            page_reviews = self._parse_current_page_reviews()
            
            if page_reviews:
                all_reviews.extend(page_reviews)
                print(f"\r페이지 {current_page_num}: +{len(page_reviews)}개 (총 {len(all_reviews)}개)", end="", flush=True)
            
            # 목표 수량 도달 체크
            if max_reviews and len(all_reviews) >= max_reviews:
                print(f"\n✓ 목표 리뷰 수({max_reviews})에 도달했습니다.")
                return all_reviews[:max_reviews]
            
            # 다음 페이지로 이동
            if not self._goto_next_page(visited_pages):
                print(f"\n✓ 모든 페이지 수집 완료 (총 {len(all_reviews)}개)")
                break
            
            current_page_num += 1
            time.sleep(2)
        
        return all_reviews
    
<<<<<<< HEAD
>>>>>>> dev
=======
>>>>>>> dev
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
        """다음 페이지로 이동. 성공하면 True, 실패하면 False 반환"""
        try:
            # 현재 페이지 확인
            try:
                current_page_elem = self.driver.find_element(
                    By.CSS_SELECTOR, 
                    "a[role='menuitem'][aria-current='true']"
                )
                current_page = current_page_elem.text.strip()
                visited_pages.add(current_page)
            except:
                pass
            
            # 페이지 네비게이션 영역 찾기
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
            
            # 다음 페이지 번호 링크 찾기
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
                # 방문하지 않은 페이지 찾기
                for link in page_links:
                    page_num = link.text.strip()
                    if page_num.isdigit() and page_num not in visited_pages:
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", link)
                        time.sleep(0.3)
                        self.driver.execute_script("arguments[0].click();", link)
                        return True
            
            # 페이지 번호가 없으면 "다음" 버튼 시도
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
    
<<<<<<< HEAD
<<<<<<< HEAD
    def _debug_review_structure(self):
        """페이지 네비게이션을 통한 리뷰 로딩"""
        retry_count = 0
        max_retries = 3
        last_count = 0
        no_change_count = 0
        visited_pages = set()  # 방문한 페이지 추적
        
        print("\n리뷰 로딩 중", end="", flush=True)
        
        # 리뷰 선택자들
        review_selectors = [
            ".HTT4L8U0CU li.PxsZltB5tV",
            ".RR2FSL9wTc > li",
            "ul[class*='review'] > li",
        ]
        
        while True:
            try:
                # 현재 페이지 확인
                try:
                    current_page_elem = self.driver.find_element(
                        By.CSS_SELECTOR, 
                        "a[role='menuitem'][aria-current='true']"
                    )
                    current_page = current_page_elem.text.strip()
                    
                    # 이미 방문한 페이지면 스킵
                    if current_page in visited_pages:
                        retry_count += 1
                        if retry_count >= max_retries:
                            print(f"\n✓ 페이지 순환 감지. (총 수집: {last_count}개)")
                            break
                    else:
                        visited_pages.add(current_page)
                        retry_count = 0
                except:
                    current_page = "?"
                
                # 현재 로드된 리뷰 수 확인
                current_count = 0
                for selector in review_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if len(elements) > current_count:
                            current_count = len(elements)
                    except:
                        continue
                
                # 진행 상황 표시
                if current_count > last_count:
                    print(f"\r리뷰 로딩 중: 페이지 {current_page}, 총 {current_count}개", end="", flush=True)
                    last_count = current_count
                    no_change_count = 0
                else:
                    no_change_count += 1
                
                # 목표 수량 도달 체크
                if max_reviews and current_count >= max_reviews:
                    print(f"\n✓ 목표 리뷰 수({max_reviews})에 도달했습니다. (로드됨: {current_count}개)")
                    return
                
                # 변화 없음 체크
                if no_change_count >= 5:
                    print(f"\n✓ 더 이상 로드할 리뷰가 없습니다. (총 {current_count}개)")
                    break
                
                # 페이지 끝까지 스크롤
                try:
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                except:
                    pass
                
                # 1. 먼저 다음 페이지 번호 클릭 시도
                next_page_found = False
                try:
                    # 여러 방법으로 페이지 네비게이션 찾기
                    pagination_selectors = [
                        "div[role='menubar']",
                        "div.w2_v0Jq7tg",  # HTML에서 본 클래스
                        "div[data-shp-area-id='pgn']",
                    ]
                    
                    pagination_div = None
                    for selector in pagination_selectors:
                        try:
                            pagination_div = self.driver.find_element(By.CSS_SELECTOR, selector)
                            break
                        except:
                            continue
                    
                    if pagination_div:
                        # 페이지 번호 링크 찾기 (여러 방법 시도)
                        page_link_selectors = [
                            "a.F0MhmLrV2F[aria-current='false']",
                            "a[role='menuitem'][aria-current='false']",
                        ]
                        
                        page_links = []
                        for selector in page_link_selectors:
                            page_links = pagination_div.find_elements(By.CSS_SELECTOR, selector)
                            if page_links:
                                break
                        
                        # 디버깅: 페이지 링크 확인
                        if not page_links and retry_count == 0:
                            all_links = pagination_div.find_elements(By.TAG_NAME, "a")
                            print(f"\n[디버깅] 페이지 네비게이션 내 모든 링크: {len(all_links)}개")
                            for link in all_links[:10]:
                                aria_current = link.get_attribute('aria-current')
                                class_name = link.get_attribute('class')
                                print(f"  - 텍스트: '{link.text}', aria-current: {aria_current}, class: {class_name[:50]}")
                        
                        if page_links:
                            # 첫 번째 비활성 페이지 클릭
                            first_link = page_links[0]
                            if first_link.is_displayed():
                                next_page_text = first_link.text
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", first_link)
                                time.sleep(0.5)
                                # JavaScript로 직접 클릭 (다른 요소에 가려지는 문제 해결)
                                self.driver.execute_script("arguments[0].click();", first_link)
                                next_page_found = True
                                print(f"→{next_page_text}", end="", flush=True)
                                time.sleep(2.5)
                                retry_count = 0
                except Exception as e:
                    if retry_count == 0:
                        print(f"\n[디버깅] 페이지 링크 오류: {str(e)[:100]}")
                    pass
                
                # 2. 페이지 번호가 없으면 "다음" 버튼 클릭 (10페이지 세트 이동)
                if not next_page_found:
                    next_button_selectors = [
                        "//a[contains(text(), '다음') and @aria-hidden='false']",
                        "//a[contains(@class, 'jFLfdWHAWX') and not(@aria-hidden='true')]",
                    ]
                    
                    button_found = False
                    for selector in next_button_selectors:
                        try:
                            button = self.driver.find_element(By.XPATH, selector)
                            if button.is_displayed():
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                                time.sleep(0.5)
                                # JavaScript로 직접 클릭
                                self.driver.execute_script("arguments[0].click();", button)
                                button_found = True
                                print(">", end="", flush=True)  # 10페이지 세트 이동 표시
                                time.sleep(2)
                                retry_count = 0
                                break
                        except:
                            continue
                    
                    if not button_found:
                        retry_count += 1
                        if retry_count >= max_retries:
                            print(f"\n✓ 더 이상 페이지가 없습니다. (총 {current_count}개)")
                            break
                        time.sleep(1)
                    
            except Exception as e:
                print(f"\n⚠️  리뷰 로딩 중 오류: {str(e)[:100]}")
                break
    
=======
>>>>>>> dev
=======
>>>>>>> dev
    def _parse_reviews(self) -> List[Dict]:
        """페이지에서 리뷰 파싱"""
        reviews = []
        
        # 페이지를 아래로 스크롤하여 모든 요소 로드
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        except:
            pass
        
        review_selectors = [
            ".HTT4L8U0CU li.PxsZltB5tV",  # 스마트스토어 리뷰
            ".RR2FSL9wTc > li",  # 브랜드스토어 리뷰
            "div.reviewItems > ul > li",  # 대체 선택자
            "li[data-review-id]",  # 리뷰 ID 속성
            "ul[class*='review'] > li",  # 리뷰 관련 ul의 li
            "ul[class*='comment'] > li",  # 댓글/리뷰 ul의 li
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
            print("\n디버깅: 페이지 구조 확인")
            
            # 스크린샷 저장 (디버깅용)
            try:
                screenshot_path = f"debug_screenshot_{int(time.time())}.png"
                self.driver.save_screenshot(screenshot_path)
                print(f"스크린샷 저장: {screenshot_path}")
            except:
                pass
            
            # 페이지 소스에서 리뷰 관련 클래스 찾기
            page_source = self.driver.page_source
            import re
            
            # class 속성에서 리뷰 관련 패턴 찾기
            class_patterns = re.findall(r'class="([^"]*review[^"]*)"', page_source, re.IGNORECASE)
            if class_patterns:
                print(f"\n발견된 리뷰 관련 클래스들:")
                unique_classes = list(set(class_patterns))[:10]
                for cls in unique_classes:
                    print(f"  - {cls}")
            
            return []
        
        for idx, element in enumerate(review_elements, 1):
            try:
                review = self._parse_review_element(element)
                if review and review.get('content') and len(review['content']) > 5:
                    reviews.append(review)
                    if idx % 10 == 0:
                        print(f"\r파싱 진행: {idx}/{len(review_elements)} ({len(reviews)}개 유효)", end="", flush=True)
            except Exception as e:
                continue
        
        print(f"\r파싱 완료: {len(review_elements)}개 처리, {len(reviews)}개 유효")
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
