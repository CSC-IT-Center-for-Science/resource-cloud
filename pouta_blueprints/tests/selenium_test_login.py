import unittest

from pouta_blueprints.tests.base import SeleniumBaseTestCase

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class LoginTestCase(SeleniumBaseTestCase):
    """ Tests basic login and logout functionality.
    """

    def test_login_as_admin(self):
        for driver in self.drivers:
            self._do_login(
                self.known_admin_email,
                self.known_admin_password,
                driver,
                wait_for_element_id="admin-dashboard"
            )
            elements = driver.find_elements_by_id("admin-dashboard")
            self.assertIsNotNone(elements)
            assert len(elements) >= 1

    def test_login_as_user(self):
        for driver in self.drivers:
            self._do_login(
                self.known_user_email,
                self.known_user_password,
                driver,
            )
            elements = driver.find_elements_by_id("user-dashboard")
            self.assertIsNotNone(elements)
            assert len(elements) >= 1

    def test_login_fail_as_user(self):
        for driver in self.drivers:
            driver.get(self.get_server_url() + "/")
            element = driver.find_element_by_id("invalid-login")
            assert not element.is_displayed()
            self._do_login(
                self.known_user_email,
                "open sesame",
                driver,
                wait_for=2
            )
            element = driver.find_element_by_id("invalid-login")
            assert element.is_displayed()
            i_should_be_empty = driver.find_elements_by_id("user-dashboard")
            assert len(i_should_be_empty) == 0

    def test_login_logout_as_user(self):
        for driver in self.drivers:
            self._do_login(
                self.known_user_email,
                self.known_user_password,
                driver
            )
            self._do_logout(driver)
            elements = driver.find_elements_by_id("user-dashboard")
            assert len(elements) == 0

    def test_frontpage(self):
        """ test more for the set-up of the system than any actual
        functionality. asserts that the front page can be loaded and the
        notification tag is present.

        It was added so that a developer doesn't get depressed when all the
        other tests fail.
        """
        driver = self.drivers[0]
        driver.get(self.get_server_url() + "/")
        wait = WebDriverWait(driver, 10)
        wait.until(EC.visibility_of_element_located((By.TAG_NAME,
                                                    "pb-notifications")))
        element = driver.find_element_by_tag_name("pb-notifications")
        self.assertIsNotNone(element)

if __name__ == "__main__":
    unittest.main()
