# Authorized Hero audio on Argo

This is the only recipe for a Hero music bed. It is deliberately remote-only:
inside `~/Videos/Wolves/Hero`, no local `ffmpeg` or `ffprobe` command is
permitted, including audio-only analysis and mux verification. That stricter
Hero rule overrides the generic local examples in
[`audio/SKILL.md`](../../audio/SKILL.md) and
[`farm.md`](../../farm.md).

This recipe is **not** an authorization decision and does not claim that an
authorized song source exists. Before submitting it, record the source's
authorization, identity, and intended excerpt in the matching
`.work-<hero>01/verify-notes.md`. Replace every angle-bracket parameter only
with values covered by that record.

## Required remote gates

The Argo pod must produce and upload all of the following:

1. `audio-format.json`: remote `ffprobe` stream and container identity.
2. `silencedetect.txt`: remote silence boundaries for the authorized source.
3. `spectrum.png`: remote spectrum for source-quality review.
4. `bed.wav`: the selected excerpt as native-rate `pcm_s24le`.
5. `bed-ebur128.txt`: integrated loudness and true peak of that bed.
6. `delivery-validation.txt`: remote AAC stream identity, clean decode, and
   decoded `ebur128` measurement.
7. `SHA256SUMS`: hashes for every returned artifact.

Keep the source's native sample rate: `NATIVE_RATE` below is read by remote
`ffprobe`, then passed unchanged to the PCM build. The only lossy generation is
the final 320k AAC mux. Do not add EQ, compression, limiting, `loudnorm`, or a
second audio encode. Select `STATIC_GAIN_DB` only from the recorded remote
measurements.

For the first authorized pass, `STATIC_GAIN_DB=0` is only a measurement
candidate, not a delivery decision. Record its decoded AAC result, derive the
single static gain, then submit a new remote pass with that recorded value.
Only the latter can be considered for delivery. Never reuse the measured AAC
as the next pass's source.

## Workflow recipe

Save this as `.work-<hero>01/<hero>01-authorized-audio.yaml`, replace its
parameters from the authorization record, then submit it from the Hero
workspace. The source and picture URLs are served to the pod; the pod does all
container reads, probes, decoding, analysis, PCM generation, muxing, and
validation.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: <hero>01-authorized-audio-
  namespace: argo
  labels:
    hero-video: <hero>01
    run-type: authorized-audio
spec:
  entrypoint: main
  serviceAccountName: argo
  arguments:
    parameters:
      - name: source-url
        value: <AUTHORIZED_SOURCE_URL>
      - name: picture-url
        value: <AUTHORIZED_PICTURE_URL>
      - name: receiver-url
        value: http://192.168.1.227:<HERO_RECEIVER_PORT>
      - name: start-seconds
        value: "<RECORDED_START_SECONDS>"
      - name: duration-seconds
        value: "<RECORDED_DURATION_SECONDS>"
      - name: static-gain-db
        value: "<MEASURED_STATIC_GAIN_DB>"
  podGC:
    strategy: OnWorkflowSuccess
  ttlStrategy:
    secondsAfterSuccess: 3600
    secondsAfterFailure: 3600
  volumeClaimTemplates:
    - metadata:
        name: work
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: local-path
        resources:
          requests:
            storage: 16Gi
  templates:
    - name: main
      dag:
        tasks:
          - name: fetch-authorized-inputs
            template: fetch
          - name: analyze-and-mux
            template: audio
            dependencies: [fetch-authorized-inputs]
          - name: upload-records-and-results
            template: upload
            dependencies: [analyze-and-mux]
    - name: fetch
      securityContext:
        fsGroup: 100
      container:
        image: curlimages/curl:8.17.0
        imagePullPolicy: IfNotPresent
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
          limits:
            cpu: "1"
            memory: 512Mi
        command: [sh, -ceu]
        args:
          - |
            curl -fsSL '{{workflow.parameters.source-url}}' -o /work/source
            curl -fsSL '{{workflow.parameters.picture-url}}' -o /work/picture.mp4
        volumeMounts:
          - name: work
            mountPath: /work
    - name: audio
      securityContext:
        fsGroup: 100
      container:
        image: lscr.io/linuxserver/ffmpeg:8.1.2-cli-ls76
        imagePullPolicy: IfNotPresent
        resources:
          requests:
            cpu: "2"
            memory: 2Gi
          limits:
            cpu: "8"
            memory: 8Gi
        command: [sh, -ceu]
        args:
          - |
            start_seconds='{{workflow.parameters.start-seconds}}'
            duration_seconds='{{workflow.parameters.duration-seconds}}'
            static_gain_db='{{workflow.parameters.static-gain-db}}'

            ffprobe -v error -of json \
              -show_entries format=filename,format_name,duration,size,bit_rate:stream=index,codec_type,codec_name,profile,sample_fmt,sample_rate,channels,channel_layout,bit_rate \
              /work/source > /work/audio-format.json
            native_rate="$(ffprobe -v error -select_streams a:0 \
              -show_entries stream=sample_rate -of default=nokey=1:noprint_wrappers=1 \
              /work/source)"
            test -n "$native_rate"

            ffmpeg -hide_banner -i /work/source \
              -af 'silencedetect=noise=-50dB:d=0.5' -f null - \
              > /work/silencedetect.txt 2>&1
            ffmpeg -hide_banner -y -i /work/source \
              -lavfi 'showspectrumpic=s=2400x1350:legend=1:scale=log' \
              -frames:v 1 /work/spectrum.png

            ffmpeg -hide_banner -y -ss "$start_seconds" -t "$duration_seconds" \
              -i /work/source -map 0:a:0 -vn -ar "$native_rate" \
              -c:a pcm_s24le /work/bed.wav
            ffmpeg -hide_banner -i /work/bed.wav \
              -af ebur128=peak=true -f null - > /work/bed-ebur128.txt 2>&1

            ffmpeg -hide_banner -y -i /work/picture.mp4 -i /work/bed.wav \
              -map 0:v:0 -map 1:a:0 -c:v copy \
              -af "volume=${static_gain_db}dB" -c:a aac -b:a 320k \
              -movflags +faststart /work/<hero>01-music-video.mp4
            {
              echo '== ffprobe =='
              ffprobe -v error -of json \
                -show_entries format=format_name,duration,size,bit_rate:stream=index,codec_type,codec_name,profile,sample_fmt,sample_rate,channels,channel_layout,bit_rate \
                /work/<hero>01-music-video.mp4
              echo '== clean decode =='
              ffmpeg -hide_banner -v error -i /work/<hero>01-music-video.mp4 -f null -
              echo '== decoded ebur128 =='
              ffmpeg -hide_banner -i /work/<hero>01-music-video.mp4 \
                -map 0:a:0 -af ebur128=peak=true -f null -
            } > /work/delivery-validation.txt 2>&1
            sha256sum /work/audio-format.json /work/silencedetect.txt \
              /work/spectrum.png /work/bed.wav /work/bed-ebur128.txt \
              /work/<hero>01-music-video.mp4 /work/delivery-validation.txt \
              > /work/SHA256SUMS
        volumeMounts:
          - name: work
            mountPath: /work
    - name: upload
      securityContext:
        fsGroup: 100
      container:
        image: curlimages/curl:8.17.0
        imagePullPolicy: IfNotPresent
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
          limits:
            cpu: "1"
            memory: 512Mi
        command: [sh, -ceu]
        args:
          - |
            receiver_url='{{workflow.parameters.receiver-url}}'
            for file in /work/audio-format.json /work/silencedetect.txt \
                /work/spectrum.png /work/bed.wav /work/bed-ebur128.txt \
                /work/<hero>01-music-video.mp4 /work/delivery-validation.txt \
                /work/SHA256SUMS; do
              curl -fsS -T "$file" "$receiver_url/$(basename "$file")"
            done
        volumeMounts:
          - name: work
            mountPath: /work
```

Use the video's dedicated receiver port. Lakshmi is **8880**; RAFI_01 and
RAFI_02 use 8878 and 8879 respectively. After Argo succeeds, append the
workflow ID, source authorization reference, exact parameters, uploaded hashes,
format identity, silence boundaries, spectrum review, native rate, bed
measurement, AAC measurement, and clean-decode result to that video's
`verify-notes.md`. Do not promote the picture or delivery until those records
are complete.
