# Authorized Hero audio on Argo

This is the only remote recipe for a Hero music bed and its delivery mux.
Inside `~/Videos/Wolves/Hero`, no local `ffmpeg` or `ffprobe` command is
permitted, including audio-only analysis and mux verification. That stricter
Hero rule overrides the generic local examples in
[`audio/SKILL.md`](../../audio/SKILL.md) and
[`farm.md`](../../farm.md).

This recipe is **not** an authorization decision and does not claim that an
authorized song source exists. Before submitting either workflow, record the
source authorization, identity, intended excerpt, expected SHA-256, and
receiver destination in the matching `.work-<hero>01/verify-notes.md`. The
sample values below make valid Argo manifests, but are deliberately
non-deliverable examples; replace parameter values only with values covered by
that record.

## Non-negotiable gates

- Delivery is 48,000 Hz. A source whose remote `ffprobe` audio stream is not
  exactly `48000` is a hard failure: re-source it. Do not resample it.
- The spectrum gate compares the RMS level after `highpass=f=16000` with the
  one-octave `8 kHz` reference band
  (`bandpass=f=8000:width_type=o:width=1`). Record the difference in dB.
  Below `-55 dB` is a hard failure; below `-46 dB` is a warning requiring
  source review.
- Do not normalize, EQ, compress, limit, or otherwise master the bed. Preserve
  its native rate and make `pcm_s24le` the lossless handoff.
- A mux candidate applies one recorded static gain to the original verified
  PCM bed and makes **one** 320k AAC encode. It never uses an earlier AAC
  candidate as input.
- Gate the decoded delivery, not the PCM. A decoded true peak at or above
  `-0.1 dBTP` hard-fails. Report the `-0.9` to `-1.1 dBTP` target range and
  warn above `-0.8 dBTP`.

AAC overshoot is non-monotonic. If the candidate is unsafe, choose the next
static-gain candidate from its returned measurements and re-submit the mux
workflow against the same original bed SHA-256. There is no fixed number of
passes and no “second-pass AAC” source.

Both workflows deliberately capture command exit status before deciding the
workflow result. Their `onExit` templates upload records even after a gate or
command failure. The upload loop skips missing early-failure artifacts, always
writes a workflow status file, and hashes every artifact that exists.

All GET inputs come from the shared source server on port **8877**. Each PUT
receiver has its own port and writes into that video's `.work-<hero>01/`
directory. A stage-1 `record-prefix` prefixes every returned bed artifact; a
stage-2 `candidate-id` prefixes every returned candidate artifact. Choose each
identifier before submission, record it in `verify-notes.md`, and never reuse
it for a different bed record or mux candidate.

## Stage 1 — bed workflow

This workflow accepts an authorized source only: it has no picture parameter or
picture dependency. It fetches and hashes the source, remotely records
`ffprobe` identity, silence boundaries, a review spectrum, and the spectral
measurements; it gates 48 kHz and source bandwidth; then it makes the original
48 kHz `pcm_s24le` bed and measures it with `ebur128`.

Save it as `.work-<hero>01/<hero>01-bed.yaml`. The example parameters are
valid YAML and must be replaced from the authorization record before use. Keep
`record-prefix` stable for this exact bed record; choose a new prefix if
building a distinct bed so its evidence cannot replace an earlier record.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: hero-bed-
  namespace: argo
  labels:
    hero-video: example-hero01
    run-type: authorized-bed
spec:
  entrypoint: bed
  onExit: upload-results
  serviceAccountName: argo
  arguments:
    parameters:
      - name: source-url
        value: http://192.168.1.227:8877/authorized-source.webm
      - name: source-sha256
        value: "0000000000000000000000000000000000000000000000000000000000000000"
      - name: receiver-url
        value: http://192.168.1.227:8880
      - name: record-prefix
        value: example-hero01-bed-v1
      - name: start-seconds
        value: "0"
      - name: duration-seconds
        value: "30"
      - name: authorization-reference
        value: example-authorization-record
  podGC:
    strategy: OnWorkflowCompletion
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
    - name: bed
      dag:
        tasks:
          - name: fetch-authorized-source
            template: fetch-authorized-source
          - name: analyze-and-build-bed
            template: analyze-and-build-bed
            dependencies: [fetch-authorized-source]
    - name: fetch-authorized-source
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
        command: [sh, -c]
        args:
          - |
            mkdir -p /work
            curl -fsSL '{{workflow.parameters.source-url}}' -o /work/source
            fetch_status=$?
            actual_sha256=""
            hash_status=1
            if [ "$fetch_status" -eq 0 ]; then
              actual_sha256="$(sha256sum /work/source | awk '{print $1}')"
              hash_status=$?
            fi
            source_match=false
            if [ "$fetch_status" -eq 0 ] &&
               [ "$hash_status" -eq 0 ] &&
               [ "$actual_sha256" = '{{workflow.parameters.source-sha256}}' ]; then
              source_match=true
            else
              fetch_status=1
            fi
            printf '%s\n' \
              "{\"source_url\":\"{{workflow.parameters.source-url}}\",\"expected_sha256\":\"{{workflow.parameters.source-sha256}}\",\"actual_sha256\":\"$actual_sha256\",\"source_match\":$source_match,\"fetch_exit_status\":$fetch_status}" \
              > /work/source-fetch-status.json
            exit "$fetch_status"
        volumeMounts:
          - name: work
            mountPath: /work
    - name: analyze-and-build-bed
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
        command: [sh, -c]
        args:
          - |
            work=/work
            overall=0
            run_to_file() {
              file=$1
              shift
              "$@" > "$work/$file" 2>&1
              command_status=$?
              printf '\nexit_status=%s\n' "$command_status" >> "$work/$file"
              if [ "$command_status" -ne 0 ]; then
                overall=1
              fi
              return 0
            }
            is_number() {
              printf '%s\n' "$1" | grep -Eq '^-?[0-9]+([.][0-9]+)?$'
            }
            source_sha256="$(sha256sum "$work/source" | awk '{print $1}')"
            run_to_file audio-format.json ffprobe -v error -of json \
              -show_entries format=filename,format_name,duration,size,bit_rate:stream=index,codec_type,codec_name,profile,sample_fmt,sample_rate,channels,channel_layout,bit_rate \
              "$work/source"
            native_rate="$(ffprobe -v error -select_streams a:0 \
              -show_entries stream=sample_rate -of default=nokey=1:noprint_wrappers=1 \
              "$work/source" 2>"$work/sample-rate.stderr")"
            sample_rate_status=$?
            printf '%s\nexit_status=%s\n' "$native_rate" "$sample_rate_status" \
              > "$work/sample-rate.txt"
            sample_rate_gate=pass
            native_rate_json=null
            if printf '%s\n' "$native_rate" | grep -Eq '^[0-9]+$'; then
              native_rate_json="$native_rate"
            fi
            if [ "$sample_rate_status" -ne 0 ] || [ "$native_rate" != "48000" ]; then
              sample_rate_gate=hard-fail
              overall=1
            fi

            run_to_file silencedetect.txt ffmpeg -hide_banner -i "$work/source" \
              -map 0:a:0 -af 'silencedetect=noise=-50dB:d=0.5' -f null -
            run_to_file spectrum.txt ffmpeg -hide_banner -y -i "$work/source" \
              -lavfi 'showspectrumpic=s=2400x1350:legend=1:scale=log' \
              -frames:v 1 "$work/spectrum.png"
            run_to_file highpass-16khz.txt ffmpeg -hide_banner -i "$work/source" \
              -map 0:a:0 -af 'highpass=f=16000,astats=metadata=1:reset=0' -f null -
            run_to_file reference-8khz.txt ffmpeg -hide_banner -i "$work/source" \
              -map 0:a:0 \
              -af 'bandpass=f=8000:width_type=o:width=1,astats=metadata=1:reset=0' \
              -f null -
            highpass_db="$(awk -F ': ' '/RMS level dB:/ {value=$NF} END {print value}' \
              "$work/highpass-16khz.txt")"
            reference_db="$(awk -F ': ' '/RMS level dB:/ {value=$NF} END {print value}' \
              "$work/reference-8khz.txt")"
            highpass_json=null
            reference_json=null
            ratio_db=""
            ratio_json=null
            high_frequency_gate=hard-fail
            if is_number "$highpass_db" && is_number "$reference_db"; then
              highpass_json="$highpass_db"
              reference_json="$reference_db"
              ratio_db="$(awk -v high="$highpass_db" -v reference="$reference_db" \
                'BEGIN {printf "%.2f", high - reference}')"
              ratio_json="$ratio_db"
              if awk -v ratio="$ratio_db" 'BEGIN {exit !(ratio < -55)}'; then
                high_frequency_gate=hard-fail
                overall=1
              elif awk -v ratio="$ratio_db" 'BEGIN {exit !(ratio < -46)}'; then
                high_frequency_gate=warning-source-review
              else
                high_frequency_gate=pass
              fi
            else
              overall=1
            fi

            bed_status=not-built
            if [ "$sample_rate_gate" = pass ] &&
               [ "$high_frequency_gate" != hard-fail ] &&
               [ "$overall" -eq 0 ]; then
              run_to_file bed-build.txt ffmpeg -hide_banner -y \
                -ss '{{workflow.parameters.start-seconds}}' \
                -t '{{workflow.parameters.duration-seconds}}' \
                -i "$work/source" -map 0:a:0 -vn -ar "$native_rate" \
                -c:a pcm_s24le "$work/bed.wav"
              if [ -f "$work/bed.wav" ]; then
                run_to_file bed-ebur128.txt ffmpeg -hide_banner -i "$work/bed.wav" \
                  -af ebur128=peak=true -f null -
                bed_status=written
              else
                overall=1
                bed_status=failed
              fi
            fi
            gate_overall=pass
            if [ "$overall" -ne 0 ]; then
              gate_overall=hard-fail
            fi
            printf '%s\n' \
              "{\"authorization_reference\":\"{{workflow.parameters.authorization-reference}}\",\"source_sha256\":\"$source_sha256\",\"sample_rate_hz\":$native_rate_json,\"sample_rate_gate\":\"$sample_rate_gate\",\"highpass_over_16khz_db\":$highpass_json,\"reference_8khz_band_db\":$reference_json,\"high_to_8khz_ratio_db\":$ratio_json,\"high_frequency_gate\":\"$high_frequency_gate\",\"bed_status\":\"$bed_status\",\"overall\":\"$gate_overall\"}" \
              > "$work/audio-gate.json"
            exit "$overall"
        volumeMounts:
          - name: work
            mountPath: /work
    - name: upload-results
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
        command: [sh, -c]
        args:
          - |
            work=/work
            receiver_url='{{workflow.parameters.receiver-url}}'
            record_prefix='{{workflow.parameters.record-prefix}}'
            printf '%s\n' \
              "{\"workflow_name\":\"{{workflow.name}}\",\"workflow_uid\":\"{{workflow.uid}}\",\"workflow_status\":\"{{workflow.status}}\",\"stage\":\"bed\"}" \
              > "$work/workflow-status.json"
            : > "$work/SHA256SUMS"
            files="source-fetch-status.json audio-format.json sample-rate.txt sample-rate.stderr silencedetect.txt spectrum.txt spectrum.png highpass-16khz.txt reference-8khz.txt bed-build.txt bed.wav bed-ebur128.txt audio-gate.json workflow-status.json"
            for file in $files; do
              if [ -f "$work/$file" ]; then
                sha256sum "$work/$file" >> "$work/SHA256SUMS"
              fi
            done
            upload_status=0
            for file in $files SHA256SUMS; do
              if [ -f "$work/$file" ]; then
                curl -fsS -T "$work/$file" \
                  "$receiver_url/$record_prefix-$file" || upload_status=1
              fi
            done
            exit "$upload_status"
        volumeMounts:
          - name: work
            mountPath: /work
```

Do not use the bed if `<record-prefix>-audio-gate.json` is not
`overall: "pass"`. A warning is recorded in `high_frequency_gate`; it is not
permission to ignore source review. Record the workflow ID, source
authorization reference, exact parameters, record prefix, every returned hash,
native rate, silence boundaries, spectrum review, ratio, and `ebur128` results
in `verify-notes.md`.

## Stage 2 — mux and validation workflow

This separate workflow fetches the **verified** picture, bed, and gate record
by URL and SHA-256. It rejects a non-passing bed gate, muxes the picture with
the original PCM bed once at the supplied candidate static gain, then remotely
checks the decoded result. It has no input or URL for a previous AAC candidate.

Save it as `.work-<hero>01/<hero>01-mux.yaml`. Submit a new instance for each
candidate gain, retaining the same verified bed URL and SHA-256 until a decoded
candidate is safe. `candidate-id` must be unique for every submission,
including a retry at the same gain; it prefixes the delivery and every returned
gate, status, and hash record.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: hero-mux-
  namespace: argo
  labels:
    hero-video: example-hero01
    run-type: authorized-mux
spec:
  entrypoint: mux
  onExit: upload-results
  serviceAccountName: argo
  arguments:
    parameters:
      - name: picture-url
        value: http://192.168.1.227:8877/picture-v1.mp4
      - name: picture-sha256
        value: "0000000000000000000000000000000000000000000000000000000000000000"
      - name: bed-url
        value: http://192.168.1.227:8877/.work-example-hero01/example-hero01-bed-v1-bed.wav
      - name: bed-sha256
        value: "0000000000000000000000000000000000000000000000000000000000000000"
      - name: bed-gate-url
        value: http://192.168.1.227:8877/.work-example-hero01/example-hero01-bed-v1-audio-gate.json
      - name: bed-gate-sha256
        value: "0000000000000000000000000000000000000000000000000000000000000000"
      - name: receiver-url
        value: http://192.168.1.227:8880
      - name: candidate-id
        value: example-hero01-gain-minus-1.0db-01
      - name: static-gain-db
        value: "-1.0"
      - name: delivery-name
        value: example-hero01-music-video.mp4
  podGC:
    strategy: OnWorkflowCompletion
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
    - name: mux
      dag:
        tasks:
          - name: fetch-verified-inputs
            template: fetch-verified-inputs
          - name: mux-and-validate
            template: mux-and-validate
            dependencies: [fetch-verified-inputs]
    - name: fetch-verified-inputs
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
        command: [sh, -c]
        args:
          - |
            work=/work
            mkdir -p "$work"
            candidate_id='{{workflow.parameters.candidate-id}}'
            fetch_record="$candidate_id-fetch-verified-inputs.txt"
            input_gate="$candidate_id-input-audio-gate.json"
            overall=0
            fetch_and_verify() {
              url=$1
              expected_sha256=$2
              destination=$3
              curl -fsSL "$url" -o "$destination"
              fetch_status=$?
              actual_sha256=""
              if [ "$fetch_status" -eq 0 ]; then
                actual_sha256="$(sha256sum "$destination" | awk '{print $1}')"
                if [ "$actual_sha256" != "$expected_sha256" ]; then
                  fetch_status=1
                fi
              fi
              printf '%s expected=%s actual=%s exit_status=%s\n' \
                "$destination" "$expected_sha256" "$actual_sha256" "$fetch_status" \
                >> "$work/$fetch_record"
              if [ "$fetch_status" -ne 0 ]; then
                overall=1
              fi
            }
            : > "$work/$fetch_record"
            fetch_and_verify '{{workflow.parameters.picture-url}}' \
              '{{workflow.parameters.picture-sha256}}' /work/picture.mp4
            fetch_and_verify '{{workflow.parameters.bed-url}}' \
              '{{workflow.parameters.bed-sha256}}' /work/bed.wav
            fetch_and_verify '{{workflow.parameters.bed-gate-url}}' \
              '{{workflow.parameters.bed-gate-sha256}}' "$work/$input_gate"
            if ! grep -Fq '"overall":"pass"' "$work/$input_gate" 2>/dev/null; then
              printf '%s\n' 'audio-gate.json is absent or did not pass' \
                >> "$work/$fetch_record"
              overall=1
            fi
            exit "$overall"
        volumeMounts:
          - name: work
            mountPath: /work
    - name: mux-and-validate
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
        command: [sh, -c]
        args:
          - |
            work=/work
            candidate_id='{{workflow.parameters.candidate-id}}'
            delivery_name="$candidate_id-{{workflow.parameters.delivery-name}}"
            delivery="$work/$delivery_name"
            mux_log="$candidate_id-mux-encode.txt"
            validation_log="$candidate_id-delivery-validation.txt"
            decoded_highpass="$candidate_id-decoded-highpass-16khz.txt"
            decoded_reference="$candidate_id-decoded-reference-8khz.txt"
            delivery_gate="$candidate_id-delivery-gate.json"
            overall=0
            : > "$work/$validation_log"
            run_append() {
              label=$1
              shift
              printf '== %s ==\n' "$label" >> "$work/$validation_log"
              "$@" >> "$work/$validation_log" 2>&1
              command_status=$?
              printf 'exit_status=%s\n' "$command_status" \
                >> "$work/$validation_log"
              if [ "$command_status" -ne 0 ]; then
                overall=1
              fi
              return 0
            }
            is_number() {
              printf '%s\n' "$1" | grep -Eq '^-?[0-9]+([.][0-9]+)?$'
            }
            ffmpeg -hide_banner -y -i "$work/picture.mp4" -i "$work/bed.wav" \
              -map 0:v:0 -map 1:a:0 -c:v copy \
              -af 'volume={{workflow.parameters.static-gain-db}}dB' \
              -c:a aac -b:a 320k -movflags +faststart "$delivery" \
              > "$work/$mux_log" 2>&1
            mux_status=$?
            printf '\nexit_status=%s\n' "$mux_status" >> "$work/$mux_log"
            if [ "$mux_status" -ne 0 ] || [ ! -f "$delivery" ]; then
              overall=1
              printf '%s\n' 'candidate was not created; validation unavailable' \
                >> "$work/$validation_log"
            else
              run_append ffprobe ffprobe -v error -of json \
                -show_entries format=format_name,duration,size,bit_rate:stream=index,codec_type,codec_name,profile,sample_fmt,sample_rate,channels,channel_layout,bit_rate \
                "$delivery"
              run_append clean-decode ffmpeg -hide_banner -v error -i "$delivery" \
                -f null -
              run_append decoded-ebur128 ffmpeg -hide_banner -i "$delivery" \
                -map 0:a:0 -af ebur128=peak=true -f null -
              ffmpeg -hide_banner -i "$delivery" -map 0:a:0 \
                -af 'highpass=f=16000,astats=metadata=1:reset=0' -f null - \
                > "$work/$decoded_highpass" 2>&1
              highpass_status=$?
              printf '\nexit_status=%s\n' "$highpass_status" \
                >> "$work/$decoded_highpass"
              ffmpeg -hide_banner -i "$delivery" -map 0:a:0 \
                -af 'bandpass=f=8000:width_type=o:width=1,astats=metadata=1:reset=0' \
                -f null - > "$work/$decoded_reference" 2>&1
              reference_status=$?
              printf '\nexit_status=%s\n' "$reference_status" \
                >> "$work/$decoded_reference"
              if [ "$highpass_status" -ne 0 ] || [ "$reference_status" -ne 0 ]; then
                overall=1
              fi
            fi

            delivery_rate=""
            delivery_rate_status=1
            delivery_sample_rate_gate=hard-fail
            delivery_rate_json=null
            if [ -f "$delivery" ]; then
              delivery_rate="$(ffprobe -v error -select_streams a:0 \
                -show_entries stream=sample_rate \
                -of default=nokey=1:noprint_wrappers=1 "$delivery" \
                2>>"$work/$validation_log")"
              delivery_rate_status=$?
              if [ "$delivery_rate_status" -eq 0 ] &&
                 [ "$delivery_rate" = "48000" ]; then
                delivery_sample_rate_gate=pass
                delivery_rate_json="$delivery_rate"
              else
                overall=1
              fi
            fi
            true_peak_db=""
            if [ -f "$delivery" ]; then
              true_peak_db="$(awk '/True peak:/ {want=1; next} want && /Peak:/ {print $(NF-1); exit}' \
                "$work/$validation_log")"
            fi
            true_peak_json=null
            true_peak_gate=hard-fail
            target_range=unmeasured
            if is_number "$true_peak_db"; then
              true_peak_json="$true_peak_db"
              if awk -v peak="$true_peak_db" 'BEGIN {exit !(peak >= -0.1)}'; then
                true_peak_gate=hard-fail
                overall=1
              elif awk -v peak="$true_peak_db" 'BEGIN {exit !(peak > -0.8)}'; then
                true_peak_gate=warning-above-minus-0.8
              else
                true_peak_gate=pass
              fi
              if awk -v peak="$true_peak_db" \
                  'BEGIN {exit !(peak >= -1.1 && peak <= -0.9)}'; then
                target_range=within-minus-0.9-to-minus-1.1
              else
                target_range=outside-minus-0.9-to-minus-1.1
              fi
            else
              overall=1
            fi

            decoded_highpass_db="$(awk -F ': ' '/RMS level dB:/ {value=$NF} END {print value}' \
              "$work/$decoded_highpass" 2>/dev/null)"
            decoded_reference_db="$(awk -F ': ' '/RMS level dB:/ {value=$NF} END {print value}' \
              "$work/$decoded_reference" 2>/dev/null)"
            decoded_ratio_json=null
            decoded_ratio_gate=hard-fail
            if is_number "$decoded_highpass_db" && is_number "$decoded_reference_db"; then
              decoded_ratio="$(awk -v high="$decoded_highpass_db" \
                -v reference="$decoded_reference_db" 'BEGIN {printf "%.2f", high - reference}')"
              decoded_ratio_json="$decoded_ratio"
              if awk -v ratio="$decoded_ratio" 'BEGIN {exit !(ratio < -55)}'; then
                decoded_ratio_gate=hard-fail
                overall=1
              elif awk -v ratio="$decoded_ratio" 'BEGIN {exit !(ratio < -46)}'; then
                decoded_ratio_gate=warning-source-review
              else
                decoded_ratio_gate=pass
              fi
            else
              overall=1
            fi
            delivery_overall=pass
            if [ "$overall" -ne 0 ]; then
              delivery_overall=hard-fail
            fi
            printf '%s\n' \
              "{\"candidate_static_gain_db\":\"{{workflow.parameters.static-gain-db}}\",\"source_bed_sha256\":\"{{workflow.parameters.bed-sha256}}\",\"delivery_sample_rate_hz\":$delivery_rate_json,\"delivery_sample_rate_gate\":\"$delivery_sample_rate_gate\",\"true_peak_dbTP\":$true_peak_json,\"true_peak_gate\":\"$true_peak_gate\",\"true_peak_target\":\"$target_range\",\"decoded_high_to_8khz_ratio_db\":$decoded_ratio_json,\"decoded_high_frequency_gate\":\"$decoded_ratio_gate\",\"overall\":\"$delivery_overall\"}" \
              > "$work/$delivery_gate"
            exit "$overall"
        volumeMounts:
          - name: work
            mountPath: /work
    - name: upload-results
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
        command: [sh, -c]
        args:
          - |
            work=/work
            receiver_url='{{workflow.parameters.receiver-url}}'
            candidate_id='{{workflow.parameters.candidate-id}}'
            workflow_status="$candidate_id-workflow-status.json"
            hashes="$candidate_id-SHA256SUMS"
            delivery_name="$candidate_id-{{workflow.parameters.delivery-name}}"
            printf '%s\n' \
              "{\"workflow_name\":\"{{workflow.name}}\",\"workflow_uid\":\"{{workflow.uid}}\",\"workflow_status\":\"{{workflow.status}}\",\"stage\":\"mux-validation\"}" \
              > "$work/$workflow_status"
            : > "$work/$hashes"
            files="$candidate_id-fetch-verified-inputs.txt $candidate_id-input-audio-gate.json $candidate_id-mux-encode.txt $candidate_id-delivery-validation.txt $candidate_id-decoded-highpass-16khz.txt $candidate_id-decoded-reference-8khz.txt $candidate_id-delivery-gate.json $delivery_name $workflow_status"
            for file in $files; do
              if [ -f "$work/$file" ]; then
                sha256sum "$work/$file" >> "$work/$hashes"
              fi
            done
            upload_status=0
            for file in $files "$hashes"; do
              if [ -f "$work/$file" ]; then
                curl -fsS -T "$work/$file" "$receiver_url/$file" || upload_status=1
              fi
            done
            exit "$upload_status"
        volumeMounts:
          - name: work
            mountPath: /work
```

Only promote a candidate when `<candidate-id>-delivery-gate.json` is
`overall: "pass"` and the returned `<candidate-id>-delivery-validation.txt`
confirms AAC 320k, clean decode, and the decoded `ebur128` result. The returned
delivery is `<candidate-id>-<delivery-name>`; a failed candidate therefore
cannot replace a passing or earlier candidate. Record every candidate ID and
gain, original bed hash, picture hash, decoded true peak, target-range status,
spectral ratio, workflow ID, and uploaded hashes in `verify-notes.md`,
including failed candidates.

Use the video's dedicated receiver port. Lakshmi is **8880**; RAFI_01 and
RAFI_02 use **8878** and **8879** respectively. That port is for PUT results
only: the example bed and gate GET URLs above intentionally use the source
server on **8877** and their `.work-example-hero01/` paths. Do not promote the
picture, bed, or delivery until the corresponding remote records are complete.
