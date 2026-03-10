import pandas as pd
from playwright.sync_api import sync_playwright


SEARCH_URL = "https://pels.texas.gov/roster/pesearch.html?ver=V062723"


def scrape_lastname_letter(letter: str, output_file: str | None = None) -> None:
    """Use the PE search page to get all PEs whose last name starts with a letter."""
    letter = letter.upper()
    if output_file is None:
        output_file = f"{letter}_PEs.csv"

    extracted: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("Navigating to the PE search page ...")
        page.goto(SEARCH_URL)
        page.wait_for_load_state("networkidle")

        # Fill Last Name with the starting letter (e.g., "A")
        print(f"Searching for last names starting with '{letter}' ...")
        # The Last Name field is the second text box in the form (after PE Number)
        text_boxes = page.get_by_role("textbox")
        last_name_input = text_boxes.nth(1)
        last_name_input.fill(letter)

        # Click the Search button
        page.click('input[value="Search 🔎"]')

        current_page = 1
        while True:
            print(f"Scraping page {current_page} ...")

            # Wait for results to appear
            page.wait_for_selector("div#result-area", state="visible")
            page.wait_for_timeout(2000)  # let Angular render fully

            header_rows = page.locator("div#result-header-row").all()
            result_rows = page.locator("div#result-row-area").all()
            

            print(f"Found {len(header_rows)} results on page {current_page}.")

            for header, result in zip(header_rows, result_rows):
                # Header typically contains name and PE number
                header_cols = header.locator(".col-sm-6").all()
                full_name = header_cols[0].inner_text().strip() if header_cols else ""

                last_name = ""
                first_name = ""
                if "," in full_name:
                    parts = [p.strip() for p in full_name.split(",", 1)]
                    last_name = parts[0]
                    first_name = parts[1] if len(parts) > 1 else ""
                else:
                    last_name = full_name
                last_name = ""
                first_name = ""
                branch = ""
                granted = ""
                expires = ""
                employer = ""

                title_rows = result.locator(".result-title-row").all()
                value_rows = result.locator(".result-value-row").all()

                for t_loc, v_loc in zip(title_rows, value_rows):
                    title = t_loc.inner_text().strip()
                    value = v_loc.inner_text().strip()
                    if title.startswith("Last Name"):
                        last_name = value
                    elif title.startswith("First Name"):
                        first_name = value
                    elif title.startswith("Branch"):
                        branch = value
                    elif title.startswith("Granted"):
                        granted = value
                    elif title.startswith("Expires"):
                        expires = value
                    elif title.startswith("Employer"):
                        employer = value

                extracted.append(
                    {
                        "Last Name": last_name,
                        "First Name": first_name,
                        "Branch": branch,
                        "Granted": granted,
                        "Expires": expires,
                        "Employer(s)": employer,
                    }
                )

            # Next page link (2, 3, ...) if present
            next_page_str = str(current_page + 1)
            next_link = page.locator(
                'xpath=//div[contains(@class, "page-links-area")]//a[normalize-space(text())="'
                + next_page_str
                + '"]'
            )

            if next_link.count() > 0:
                next_link.first.click()
                current_page += 1
            else:
                break

        browser.close()

    print(f"Total rows extracted for '{letter}': {len(extracted)}")
    df = pd.DataFrame(extracted)

    # Keep only Civil Engineering records
    df = df[df["Branch"].str.contains("Civil", case=False, na=False)]

    print(f"Total Civil Engineering rows for '{letter}': {len(df)}")
    df.to_csv(output_file, index=False)
    print(f"Data saved to {output_file}")


if __name__ == "__main__":
    # Change this list if you only want certain letters
    letters = ["A"]

    for lt in letters:
        print("=" * 60)
        scrape_lastname_letter(lt)
    
