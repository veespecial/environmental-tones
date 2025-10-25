<?php
header('Content-Type: application/json');

$jsonFile = __DIR__ . '/playlist.json';

$playlist = [
    'current' => ['title' => 'Unknown', 'artist' => 'Unknown'],
    'recent' => []
];
if (file_exists($jsonFile)) {
    $data = json_decode(file_get_contents($jsonFile), true);
    if (is_array($data)) {
        $playlist = array_merge($playlist, $data);
    }
}

function getCurrentSong() {
    $streamUrl = "https://listen.radioking.com/radio/712013/stream/777593";
    $context = stream_context_create([
        'http' => [
            'method' => 'GET',
            'header' => "Icy-MetaData:1\r\nUser-Agent: PHP-NowPlaying/1.0\r\n",
            'timeout' => 5
        ]
    ]);

    $fp = @fopen($streamUrl, 'r', false, $context);
    if (!$fp) return null;

    $metaInt = null;
    foreach ($http_response_header as $h) {
        if (stripos($h, 'icy-metaint:') === 0) {
            $metaInt = (int)substr($h, 12);
            break;
        }
    }

    if (!$metaInt) {
        fclose($fp);
        return null;
    }

    $data = stream_get_contents($fp, $metaInt + 255);
    fclose($fp);

    if (strlen($data) <= $metaInt) return null;

    $metaData = substr($data, $metaInt);
    $len = ord($metaData[0]) * 16;
    if ($len <= 0) return null;

    $metaStr = substr($metaData, 1, $len);
    $metaStr = trim($metaStr, "\0");
    $metaStr = html_entity_decode($metaStr, ENT_QUOTES);

    if (preg_match("/StreamTitle='(.*?)';/s", $metaStr, $matches)) {
        $song = trim($matches[1]);
        if ($song === '') return null;

        if (stripos($song, ' - ') !== false) {
            [$artist, $title] = explode(' - ', $song, 2);
        } else {
            $artist = 'Unknown';
            $title = $song;
        }

        return [
            'artist' => trim($artist),
            'title' => trim($title)
        ];
    }

    return null;
}

$current = getCurrentSong();

if ($current && $current['title'] !== 'Unknown' && $current['artist'] !== 'Unknown') {
    $prev = $playlist['current'];

    $isNew = !(
        strtolower($prev['title']) === strtolower($current['title']) &&
        strtolower($prev['artist']) === strtolower($current['artist'])
    );

    if ($isNew) {
        if ($prev['title'] !== 'Unknown' && $prev['artist'] !== 'Unknown') {
            array_unshift($playlist['recent'], $prev);
        }

        $playlist['recent'] = array_filter($playlist['recent'], function ($song) use ($current) {
            return !(
                strtolower($song['title']) === strtolower($current['title']) &&
                strtolower($song['artist']) === strtolower($current['artist'])
            );
        });

        $playlist['recent'] = array_slice(array_values($playlist['recent']), 0, 10);

        $playlist['current'] = $current;

        file_put_contents($jsonFile, json_encode($playlist, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES));
    }
}

echo json_encode($playlist);