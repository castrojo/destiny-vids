# Trailer URL hold design

## Purpose

The trailer song ends with the current 1:50 cut. The URL needs five more seconds of screen time after the song ends.

## Timing

The existing picture and audio remain unchanged through 110.020 seconds. The final KubeCon card then remains visible for five silent seconds.

The new total duration is 115.020 seconds. The extra hold does not extend, loop, fade, or process the song.

## Build changes

The canonical builder must use separate durations for the music and the complete trailer. The end card must include the five-second hold.

The trailer record must describe the new timing. The builder must continue to create the lossless master at its normal delivery path.

The social copy must be regenerated from the new master. It must not use the old social copy as its source.

## Verification

The master and social copy must have a duration of approximately 115.020 seconds. Their audio must end at approximately 110.020 seconds.

Both files must decode without errors. The master must meet the project audio peak requirement.

A frame from the final second must show the KubeCon card and `wolves.projectbluefin.io`. The five-second hold must contain no unintended frozen transition or repeated audio.
