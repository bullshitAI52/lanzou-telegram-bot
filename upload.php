<?php
// Dedicated upload entrypoint. Nginx routes this file to the upload-only FPM pool.
require __DIR__ . '/api.php';
