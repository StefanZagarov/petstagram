import os
import shutil
from io import BytesIO
from unittest.mock import Mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from photos.forms import PhotoCreateForm, PhotoEditForm
from photos.validators import validate_file_size

from .models import Photo

# ── Test media isolation ──────────────────────────────────────────────────────
# Any test that SAVES a Photo writes a real image file to MEDIA_ROOT. Left alone
# that dumps junk like `test_<random>.jpg` into the project's real media/images/.
# So file-writing tests inherit MediaTestCase below, which redirects MEDIA_ROOT to
# a throwaway `test_media/` folder (see test_media/README.md) and wipes it after
# each test. Tests that only build/validate in memory (the validator, model
# full_clean, form is_valid) never touch disk, so they stay on plain TestCase.
TEST_MEDIA_ROOT = os.path.join(settings.BASE_DIR, "test_media")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class MediaTestCase(TestCase):
    """Base TestCase for tests that persist a Photo (and therefore write a file).

    `@override_settings(MEDIA_ROOT=...)` swaps the media folder for the lifetime of
    these tests so uploads land in `test_media/` instead of the real `media/`.
    `tearDown` then deletes the generated `images/` subfolder so nothing leaks
    between tests or runs. Subclasses inherit both the override and the cleanup, so
    a file-writing test class just needs to subclass this instead of TestCase.
    """

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(os.path.join(TEST_MEDIA_ROOT, "images"), ignore_errors=True)


class PhotoTestsNoUser(TestCase):
    """Unit tests for the standalone `validate_file_size` validator.

    Principle: a plain validator function is logic YOU wrote, so test it
    directly — no model, no database, no form. Hand it a Mock that carries
    ONLY what the code actually reads (`.size`); `spec=["size"]` makes the
    fake error loudly if the code ever reaches for anything else, keeping the
    fake honest. Test the EXACT boundary (5_242_880), not a value comfortably
    over/under, so an off-by-one (`>` vs `>=`) can't slip through.
    """

    def test_custom_size_validator_file_too_big(self):
        # 1. Arrange
        image = Mock(spec=["size"])
        # Over the limit by 1 byte
        image.size = 5242881

        # 2. & 3. Act & Assert (can't capture a raise, would throw an error in the test itself)
        # When you expect an exception, you wrap the call in a with self.assertRaises(...) block. If the code inside raises that exception, the test passes; if it doesn't raise, the test fails. The `with` wraps around the call so it can intercept the exception as it escapes. You can't catch an exception by looking at a variable after it — you have to be wrapped around the code while it raises.
        with self.assertRaises(ValidationError):
            validate_file_size(image)

    def test_custom_size_validator_happy_path(self):
        # 1. Arrange
        image = Mock(spec=["size"])
        # Right at the ceiling
        image.size = 5242880

        # 2. & 3. Act & Assert (function returns nothing so we just expect to get no exception here in order to pass)
        validate_file_size(image)


class PhotoTestsUser(TestCase):
    """Model-validation tests — the rules declared on the Photo model itself.

    Principle: model rules (custom validators, field constraints) only fire on
    `full_clean()` — NOT on construction and NOT on `.save()`. So build a real
    instance and call `full_clean()`. Make every OTHER field valid so the field
    under test is the only possible cause of failure ("fail for the right
    reason"). A real Photo needs its required fields: a user (FK) + an image.
    Invalid input => full_clean() RAISES ValidationError (use assertRaises).

    Gotcha learned here: CharField `max_length` IS enforced by full_clean();
    TextField `max_length` is NOT (it's only a form-level / widget hint).
    """

    # Works, but can be improved
    # def setUp(self):
    #     # Create a mock user. Since we have customized this project to accept email for login and not username, which we have omitted, we do not provide a username
    #     self.user = get_user_model().objects.create_user(
    #         email="test@test.com", password="testpass"
    #     )
    #     # Mock an image object to act as a genuine image upload
    #     self.image = SimpleUploadedFile("test.jpg", b"file content")

    # Why the split? The user is a DB row — make it once in setUpTestData (cheap, shared, auto-rolled-back). The image is a file object whose read pointer gets consumed when validated — so you want a fresh one per test via setUp, or a later test could get an already-read, empty file.
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpass"
        )

    def setUp(self):
        self.image = SimpleUploadedFile("test.jpg", b"file content")

    def test_min_length_validator_expect_raise(self):
        # 1. Arrange
        # Create the actual photo
        photo = Photo(photo=self.image, description="test12345", user=self.user)

        # 2. & 3. Act & Assert
        # This is the method that runs every field's validators (including your MinLengthValidator). Constructing a Photo does not validate it; only full_clean() (or saving through a form) does.
        with self.assertRaises(ValidationError):
            photo.full_clean()

    def test_min_length_and_max_length_validator_happy_path(self):
        photo = Photo(
            photo=self.image,
            description="This description is definitely more than 10 characters long",
            user=self.user,
        )

        photo.full_clean()

    def test_no_description_should_not_run_validator(self):
        photo = Photo(photo=self.image, user=self.user)

        # If this passes then the description min value validator does not run on empty description
        photo.full_clean()

    def test_location_max_length_validator_expect_raise(self):
        photo = Photo(
            photo=self.image,
            location="Lorem ipsum dolor sit amet consectetur adipiscing elit quisque faucibus ex sapien vitae pellentesque sem placerat in id cursus mi pretium tellus duis convallis tempus leo eu aenean sed diam.",
            user=self.user,
        )

        with self.assertRaises(ValidationError):
            photo.full_clean()


class PhotoFormCreate(TestCase):
    """Form-validation tests for PhotoCreateForm.

    Principle: a form receives RAW submitted input, not a model object —
    `data` (text fields) and `files` (uploads), mirroring request.POST /
    request.FILES. It reports validity by RETURNING from `is_valid()`
    (True/False) and stashing problems in `form.errors` — it does NOT raise
    (so use assertTrue/assertFalse + assertIn, never assertRaises). FK fields
    are submitted as a pk (`user.pk`). The form's ImageField runs Pillow to
    verify real image bytes, so build a genuine in-memory image. This is the
    layer that catches what the model can't, e.g. TextField max_length.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpass"
        )

    def setUp(self):
        # Create actual image in memory so the form accepts the proper data structure
        buffer = BytesIO()
        Image.new("RGB", (1, 1)).save(buffer, format="PNG")
        self.image = SimpleUploadedFile(
            "test.jpg", buffer.getvalue(), content_type="image/png"
        )

    def test_valid_creation_form_input(self):
        data = {
            "description": "This is a valid description",
            "location": "Somewhere in the milky galaxy",
            "user": self.user.pk,
        }
        files = {"photo": self.image}
        form = PhotoCreateForm(data, files)

        self.assertTrue(form.is_valid())

    def test_form_raise_exception_description_too_long(self):
        data = {
            "description": "a" * 301,
            "location": "Nowhere and everywhere",
            "user": self.user.pk,
        }
        files = {"photo": self.image}

        form = PhotoCreateForm(data, files)

        self.assertFalse(form.is_valid())
        self.assertIn("description", form.errors)


class PhotoFormEdit(TestCase):
    """Form-configuration test for PhotoEditForm.

    Principle: when a form customizes WHICH fields it exposes (Meta `fields` /
    `exclude`), that choice is your logic — so test it. Inspect `form.fields`
    (the dict of inputs the form renders) with assertIn / assertNotIn. Pure and
    fast: an empty form, no data, no database, no values involved.
    """

    # Testing if it really omits the photo field
    def test_edit_form_doesnt_have_photo_field(self):
        form = PhotoEditForm()
        self.assertNotIn("photo", form.fields)
        self.assertIn("description", form.fields)


class PhotoDetailsView(MediaTestCase):
    """View test for `photo_details` — a READ-ONLY render view (GET, no DB writes).

    Principle: a view test isn't about a value or a form's verdict — it's about
    the HTTP round-trip. You send a real request with the test client and inspect
    the RESPONSE the view hands back. For a read-only render view there's no
    side-effect to check, so you assert the three things the view promises the
    browser:
      1. status code 200 -> the URL resolved, the view ran, nothing crashed
      2. correct template -> it rendered the page you intended
      3. context["photo"] is the photo you asked for -> the real logic: pk in,
         correct object out.

    setUpTestData vs setUp (decided by: does each test consume/mutate the thing?):
      - No  -> setUpTestData (built once, shared, rolled back after the class).
      - Yes -> setUp (rebuilt fresh before every test).
    Here every test just sends a GET and reads the response; nothing mutates the
    photo, so it's built once in setUpTestData.
    """

    @classmethod
    def setUpTestData(cls):
        # The view does Photo.objects.get(pk=pk) -> a DATABASE query. So the photo
        # must be SAVED (have a real row + pk), not just built in memory. That's why
        # we use .objects.create() here, unlike the model tests which only did
        # Photo(...) + full_clean() and never touched the DB.
        cls.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpass"
        )
        # `image` is a throwaway local: ImageField reads it once during create()
        # to write the file, then we never need it again -> no cls. prefix.
        image = SimpleUploadedFile("test.jpg", b"file content")
        cls.photo = Photo.objects.create(
            photo=image, description="This description is totally legit", user=cls.user
        )

    def test_details_page_loads_correct_photo(self):
        # reverse() builds the URL from its name= in urls.py and fills the <int:pk>.
        # We don't hardcode "/3/photo-details/" so a URL change can't break this test
        # for the wrong reason. The pk lives on the saved photo (DB-assigned).
        url = reverse("photo-details", kwargs={"pk": self.photo.pk})
        # self.client is a fake browser (free from TestCase). .get(url) actually runs
        # URL routing + the view and returns the response object it produced.
        response = self.client.get(url)
        # 1. The page loaded successfully (200). A broken URL/import/template would
        #    surface here as a 404/500 instead.
        self.assertEqual(response.status_code, 200)
        # 2. The view rendered the template we intended (catches a wrong/typo'd path).
        self.assertTemplateUsed(response, "photos/photo-details-page.html")
        # 3. The actual logic: the view put OUR photo in the context under "photo".
        #    response.context is the dict the view rendered with; this proves pk->object.
        self.assertEqual(response.context["photo"], self.photo)


class PhotoCreateView(MediaTestCase):
    """View tests for `photo_add` — a view that serves TWO paths, so it needs TWO tests.

    Principle: a form-handling view is a fork. A GET renders the empty form;
    a POST processes a submission. Test both halves:
      - GET  -> the page shows: status 200, right template, "form" in context.
                Proves the page is reachable and renders. (the easy half)
      - POST -> the real work: a valid submission must actually CREATE a row and
                redirect. This is where a view test earns its keep — it tests the
                SIDE EFFECT, not just a rendered page.

    POST happy-path, the three things that matter:
      1. Authenticate first. self.client is AnonymousUser by default, but the view
         runs `photo.user = request.user`. A user ROW in the DB is not a logged-in
         user — those are two steps. So `self.client.force_login(self.user)` makes
         the client send the request AS that user (force_login skips the password
         check, unlike login()).
      2. Build the POST body. Required model fields only (photo + user; the rest are
         blank=True). An FK is submitted as a pk (`user.pk`). With the test client
         the uploaded file goes INSIDE `data=` (the client handles multipart) — not
         a separate `files=` like when you instantiate a form directly.
      3. Assert the outcome:
         - redirect: success ends in `redirect("home")` => HTTP 302 (NOT 201 — that's
           a REST/API convention; a server-rendered view redirects). Use
           `assertRedirects(response, reverse("home"))` — it checks the 302 AND the
           target in one call. (Mental model: render() -> 200 + context;
           redirect() -> 302 and `response.context is None`, no template was rendered.)
         - side effect: `Photo.objects.count() == 1` proves a row was really created.
         - correct logic: fetch it and assert `.user == self.user` proves the view
           stamped request.user onto the saved photo.

    setUpTestData vs setUp: the user is a shared DB row (built once, rolled back) ->
    setUpTestData. The image is a file whose read pointer is consumed during
    validation -> rebuilt fresh per test in setUp so no test gets an emptied file.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpass"
        )

    def setUp(self):
        buffer = BytesIO()
        Image.new("RGB", (1, 1)).save(buffer, format="PNG")
        self.image = SimpleUploadedFile(
            "test.jpg", buffer.getvalue(), content_type="image/png"
        )

    # View
    def test_add_photo_page_shows_correctly(self):
        url = reverse("photo-add")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "photos/photo-add-page.html")
        self.assertIn("form", response.context)

    # Create
    def test_add_photo_successfully(self):
        # 1. Force login to the test browser
        self.client.force_login(self.user)
        # 2. Get the url
        url = reverse("photo-add")
        # 3. Make a POST request with the required fields (image and user)
        response = self.client.post(
            url, data={"photo": self.image, "user": self.user.pk}
        )
        # 4. Check if it redirects to the correct page
        self.assertRedirects(response, reverse("home"))
        # 5. Check if the photo is created
        self.assertEqual(Photo.objects.count(), 1)
        # 6. Check if the created photo links to the right user
        created_photo = Photo.objects.first()
        self.assertEqual(created_photo.user, self.user)


class PhotoEditView(MediaTestCase):
    """View tests for `edit` — the GET/POST fork applied to MODIFYING an existing row.

    Principle: like photo_add this is a GET/POST fork, but it operates on a row that
    must ALREADY exist (the view opens with `Photo.objects.get(pk=pk)`). So setUp
    builds a real saved photo for every test — and because the POST test MUTATES it,
    each test needs its own fresh copy, which is exactly why the photo lives in setUp,
    not setUpTestData.

      - GET  -> the edit page renders: status 200, right template, "form" in context.
      - POST -> submit a CHANGED value and prove it PERSISTED. PhotoEditForm uses
                `exclude = ["photo"]`, so the body carries the changed field + the
                required user pk and NO photo. Success redirects to photo-details
                (with pk), not home.

    The gotcha that defines this test: after the POST, `self.photo` is a STALE
    in-memory object — the view changed the DB ROW, not your Python instance. Call
    `self.photo.refresh_from_db()` (or re-fetch) before asserting, or you'd be
    checking the old description and the test would prove nothing.
    """

    # setUpTestData: a CLASS-level hook (note @classmethod + cls). Runs ONCE for the
    # whole class, inside a transaction that's rolled back only after the LAST test.
    # Use it for shared, READ-ONLY fixtures — here the user is just an FK target the
    # edit tests never change, so building it once and sharing it is the cheap choice.
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpass"
        )

    # setUp: an INSTANCE-level hook (self). Runs BEFORE EVERY test, giving each one a
    # brand-new copy. Use it for anything a test CONSUMES or MUTATES:
    #   - the image's read pointer is consumed during validation -> needs to be fresh,
    #   - the photo gets MUTATED by the edit POST test -> each test must start from a
    #     clean, unedited row so tests can't bleed into one another.
    # Rule of thumb: read-only & shared -> setUpTestData; consumed/mutated -> setUp.
    def setUp(self):
        buffer = BytesIO()
        Image.new("RGB", (1, 1)).save(buffer, format="PNG")
        self.image = SimpleUploadedFile(
            "test.jpg", buffer.getvalue(), content_type="image/png"
        )
        self.photo = Photo.objects.create(
            photo=self.image, user=self.user, description="A normal description"
        )

    # View
    def test_edit_photo_page_shows_correctly(self):
        # 1. Get the endpoint url
        url = reverse("photo-edit", kwargs={"pk": self.photo.pk})
        # 2. Make the request with the test client
        response = self.client.get(url)
        # 3. Check if we get ok status (200)
        self.assertEqual(response.status_code, 200)
        # 4. Check if we get the correct page (template)
        self.assertTemplateUsed(response, "photos/photo-edit-page.html")
        # 5. Check if we have the form in the page
        self.assertIn("form", response.context)

    # Edit
    def test_edit_photo_successfully(self):
        # 1. Get the page url
        url = reverse("photo-edit", kwargs={"pk": self.photo.pk})
        # 2. Change the description field value, POST to update it
        response = self.client.post(
            url, data={"description": "An updated description", "user": self.user.pk}
        )
        # 3. Check if we redirected properly
        self.assertRedirects(
            response, reverse("photo-details", kwargs={"pk": self.photo.pk})
        )
        # 4. Check if the field has been updated. Since self.photo is now a stale object, we need to pull the updated photo object from the database
        self.photo.refresh_from_db()
        self.assertEqual(self.photo.description, "An updated description")


class PhotoDeleteView(MediaTestCase):
    """View test for `photo_delete` — the mirror of create: prove a row DISAPPEARS.

    Principle: this view has no form and no `if form.is_valid()`. It fetches the
    photo, deletes it, and redirects to home — on ANY request method. So it's a
    SINGLE test, not a GET/POST pair. setUp creates the photo to be deleted (a
    mutation, hence per-test in setUp).

    Assert two things: it redirected to home, and the side effect really happened —
    `Photo.objects.count() == 0` proves the row is gone (the inverse of create's
    `== 1`).

    Documented design smell: deleting on a GET is bad practice — destructive actions
    should require POST. The test uses GET to match the view AS WRITTEN; the day the
    view is hardened to require POST this test will start failing, which is the test
    doing its job of pinning down current behaviour.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpass"
        )

    def setUp(self):
        buffer = BytesIO()
        Image.new("RGB", (1, 1)).save(buffer, format="PNG")
        self.image = SimpleUploadedFile(
            "test.jpg", buffer.getvalue(), content_type="image/png"
        )
        self.photo = Photo.objects.create(
            photo=self.image, user=self.user, description="A normal description"
        )

    def test_delete_photo_successfully(self):
        url = reverse("photo-delete", kwargs={"pk": self.photo.pk})
        # Here we have a code smell - operations like delete should be made only by POST reqeusts as a good practice. The moment this is fixed, the test will fail, but this is kind of the idea - we test that the bad practice is still in play, so passing here (in real project) would mean we keep a bad design choice
        response = self.client.get(url)
        # assertRedirects already verifies status code so self.assertEquals(response.status_code, 302) is redundant
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(Photo.objects.count(), 0)
