# test_media/

Throwaway media root used **only by the test suite**.

Tests that save a `Photo` write a real image file to `MEDIA_ROOT`. To keep the
project's real `media/` folder clean, `photos/tests.py` defines a `MediaTestCase`
base class decorated with `@override_settings(MEDIA_ROOT=<this folder>)`. Any test
that persists a photo subclasses it, so its uploads land here instead of in
`media/`.

The generated `images/` subfolder is wiped after every test (`tearDown` →
`shutil.rmtree`), so this directory should normally hold nothing but this README.
The `images/` content is git-ignored; this README is kept so the folder's purpose
is self-documenting.
