#!/bin/bash
# Assembles "Jack & Lexie's Big Day Out" (8:00) from the Higgsfield assets. Run inside the Higgsfield sandbox.
# Env: UPLOAD_URL (presigned PUT for the final mp4). Output: out/episode.mp4
set -euo pipefail
cd /home/user; mkdir -p src seg out
H=https://d8j0ntlcm91z4.cloudfront.net/user_3J8Na3IQJEUtBerYQQOxXHpH4Y4
W=1920; HT=1080; FPS=24
FONT=$(find / -iname "Montserrat-Bold*.ttf" 2>/dev/null | head -1); [ -z "$FONT" ] && FONT=$(find / -iname "*Bold*.ttf" 2>/dev/null | head -1); [ -z "$FONT" ] && FONT=$(find / -iname "*.ttf" 2>/dev/null | head -1)
FONTR=$(find / -iname "Montserrat-Regular*.ttf" 2>/dev/null | head -1); [ -z "$FONTR" ] && FONTR=$FONT
echo "font=$FONT" 
dl(){ [ -f "src/$2" ] || curl -sf -m 120 -L -o "src/$2" "$1"; }
# ---- assets ----
declare -A ST
ST[S1]=hf_20260913_232541_efc95772-638a-487e-9ff1-694c296ead87.png
ST[S3]=hf_20260913_232540_a8136922-87b4-4df3-8865-5c6d8c2fb4eb.png
ST[S4]=hf_20260913_232541_5518f27b-c49b-4727-bc64-702532400d1e.png
ST[S5]=hf_20260913_233252_3abf0abb-55cf-4ab6-8507-84c632d83ccc.png
ST[S6]=hf_20260913_232540_61616d0c-2023-4d3b-99b1-329849a76d29.png
ST[S7]=hf_20260913_232540_e1e03289-ce9f-4d6b-9746-cbc673fc749b.png
ST[S8]=hf_20260913_232540_ba7a5d2f-6eaf-4d07-9fc2-4f0a220be56e.png
ST[S9]=hf_20260913_233252_c38fad01-769b-46cb-9647-333a7900e336.png
ST[S13]=hf_20260913_233252_b10d3f6f-62a6-4e00-bc89-faac3ec31232.png
ST[S14]=hf_20260913_233252_1d54c42e-11cd-47bd-ab5d-ac956246cf95.png
ST[S15]=hf_20260913_233252_366b5d10-d031-45a2-a4b1-15f0072a09ce.png
ST[S16]=hf_20260913_233349_9fe6e292-e7dc-40ce-af96-3eeee4d54f98.png
ST[S17]=hf_20260913_233350_7d1e5abf-4070-4491-b0d0-b9efc9d9d776.png
ST[S18]=hf_20260913_233349_f0855a5f-a047-4465-9a72-0eff27059046.png
ST[S19]=hf_20260913_233349_e01bde22-9b2f-4dd0-a402-48f6ede6650e.png
ST[S20]=hf_20260913_233349_d2f6c6a7-a965-411e-850c-3b000b376db4.png
ST[S21]=hf_20260913_233349_ca122e9c-8d29-4da2-907d-403205f2b7e2.png
ST[S22]=hf_20260913_233349_bc06a027-0d67-4a8c-a6b7-0c3b15689b53.png
ST[S23]=hf_20260913_233154_0914c60d-78da-4350-854b-17f4ea2b89f3.png
ST[S24]=hf_20260913_233154_0a585129-3640-4e95-8130-ad21f2fcabf2.png
ST[S25]=hf_20260913_233153_08f3e9e0-c4d1-4e7c-9bbd-0b084ad85926.png
ST[S26]=hf_20260913_233153_4b0d5767-1ec8-409b-be2c-42a52cd17c57.png
ST[S27]=hf_20260913_233154_fe05eb01-abb1-4122-91a7-18b2fd72cc22.png
ST[S28]=hf_20260913_233154_689a9301-46c9-44f6-ae9d-df906035bb09.png
ST[S29]=hf_20260913_233155_be8324e7-3256-417e-a4d5-e0a7539cc6e9.png
ST[S30]=hf_20260913_233154_3a6e5e73-7307-4ce0-b9ad-f474bc3bd0a9.png
ST[S31]=hf_20260913_233153_07083e8e-bcb2-4d3d-ad74-5e15d8d559a8.png
ST[S32]=hf_20260913_233153_ff50798a-a2f8-4506-bd03-c8eab779e47e.png
ST[S33]=hf_20260913_233154_f8df1810-7ac2-4524-b9da-8ef9186d7442.png
ST[S34]=hf_20260913_233154_2f0c6c34-3261-41e2-91c4-c7879e5f8344.png
ST[S35]=hf_20260913_233452_f535387c-33f1-47bd-956c-62b7d262c293.png
ST[S36]=hf_20260913_233532_4f9afce4-55b2-49f2-b3dc-0f9ffa913dd5.png
ST[S37]=hf_20260913_233452_b3b8ed64-174d-4eac-a195-0781c23f3b7f.png
ST[S38]=hf_20260913_233452_e9a1031d-673e-49ca-9388-f772049bc5e8.png
ST[S39]=hf_20260913_233452_779e58f0-1360-4dda-9bbb-6cde839811cb.png
ST[P9]=hf_20260913_225557_863009dd-8f1b-4dea-a173-a9010741e392.png
declare -A VC
VC[V1]=hf_20260913_233955_e8237d0d-de03-4eaa-8493-cb39f5d8394e.mp4
VC[V2]=hf_20260913_233955_6617ace6-e3cf-4900-b30b-a07d9c600e2f.mp4
VC[V3]=hf_20260913_233955_610baed5-2bf3-4f6b-8804-bdc16b77fe8f.mp4
VC[V4]=hf_20260913_233724_b2574d33-efb3-4d55-ab02-abc927693106.mp4
VC[V5]=hf_20260913_234335_9999499b-86be-43a6-97cb-47888937a055.mp4
VC[V6]=hf_20260913_234335_744d6fd6-a141-4f03-a4c0-a4394939041a.mp4
VC[V7]=hf_20260913_233724_0e5e154b-bbbd-44bf-8d2f-b45b9b34285b.mp4
VC[V8]=hf_20260913_233724_09303d46-1b50-4d30-a184-c516b7bc9ede.mp4
VC[V9]=hf_20260913_233725_2eb822ef-6aba-4e2c-9270-6e1c907207ea.mp4
VC[V10]=hf_20260913_233724_db6904af-35b4-413d-9c40-98a15e7b5057.mp4
VC[V11]=hf_20260913_234335_6a288650-b029-4ac6-8f58-f9ae6ea0761c.mp4
VC[V12]=hf_20260913_233724_6e023b93-07af-43f4-9c2a-9d6cf650207f.mp4
VC[V13]=hf_20260913_234037_a82b4693-891f-4651-9564-2cd02602a63a.mp4
VC[V14]=hf_20260913_234037_409d5903-64e4-472c-991a-d763180789df.mp4
for k in "${!ST[@]}"; do dl "$H/${ST[$k]}" "$k.png"; done
for k in "${!VC[@]}"; do dl "$H/${VC[$k]}" "$k.mp4"; done
dl "$H/hf_20260913_235512_e095e732-c930-4ed4-b8b1-9b07cf15687e.mp3" vo.mp3
dl "https://gcdn.picsart.com/editing-temp/768a5dae-ae9c-42e9-8403-e572dedb6a1b.mp3" music.mp3
echo "downloaded $(ls src | wc -l) files"
ENC="-c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -r $FPS -an"
# ---- shot builders ----
push(){ # still with slow push-in: $1 name $2 file $3 dur
  N=$(( $3 * FPS ))
  ffmpeg -loglevel error -y -loop 1 -framerate $FPS -i "src/$2" -t $3 -vf "scale=2016:1134:force_original_aspect_ratio=increase,crop=2016:1134,zoompan=z='1+0.05*on/$N':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=${W}x${HT}:fps=$FPS,format=yuv420p" $ENC "seg/$1.mp4"
}
pan(){ # 21:9 still panned: $1 name $2 file $3 dur $4 dir (r|l)
  if [ "$4" = r ]; then X="(iw-ow)*t/$3"; else X="(iw-ow)*(1-t/$3)"; fi
  ffmpeg -loglevel error -y -loop 1 -framerate $FPS -i "src/$2" -t $3 -vf "scale=-2:$HT,crop=$W:$HT:x='$X':y=0,format=yuv420p" $ENC "seg/$1.mp4"
}
clip(){ # $1 name $2 file $3 dur
  ffmpeg -loglevel error -y -i "src/$2" -vf "scale=$W:$HT:force_original_aspect_ratio=increase,crop=$W:$HT,fps=$FPS,tpad=stop_mode=clone:stop_duration=3,format=yuv420p" -t $3 $ENC "seg/$1.mp4"
}
card(){ # $1 name $2 text $3 dur
  printf '%s' "$2" > seg/$1.txt
  ffmpeg -loglevel error -y -f lavfi -i "color=c=0x1F4E9A:s=${W}x${HT}:d=$3:r=$FPS" -vf "drawtext=fontfile='$FONT':textfile=seg/$1.txt:fontcolor=0xFFD23F:fontsize=96:x=(w-tw)/2:y=(h-th)/2,fade=t=in:st=0:d=0.3,fade=t=out:st=$(awk "BEGIN{print $3-0.3}"):d=0.3,format=yuv420p" $ENC "seg/$1.mp4"
}
title(){ # title overlay on S3 push: $1 name $2 file $3 dur
  N=$(( $3 * FPS )); printf '%s' "Jack & Lexie's Big Day Out" > seg/t1.txt; printf '%s' "Dog TV in colors your dog can see" > seg/t2.txt
  ffmpeg -loglevel error -y -loop 1 -framerate $FPS -i "src/$2" -t $3 -vf "scale=2016:1134:force_original_aspect_ratio=increase,crop=2016:1134,zoompan=z='1+0.05*on/$N':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=${W}x${HT}:fps=$FPS,drawbox=x=0:y=h-360:w=iw:h=360:color=0x1F4E9A@0.88:t=fill:enable='gte(t,0.4)',drawtext=fontfile='$FONT':textfile=seg/t1.txt:fontcolor=0xFFD23F:fontsize=100:x=(w-tw)/2:y=h-300:alpha='if(lt(t,0.4),0,min(1,(t-0.4)*2))',drawtext=fontfile='$FONTR':textfile=seg/t2.txt:fontcolor=0xFFF6D6:fontsize=44:x=(w-tw)/2:y=h-150:alpha='if(lt(t,0.9),0,min(1,(t-0.9)*2))',format=yuv420p" $ENC "seg/$1.mp4"
}
endcard(){ # $1 name $2 dur
  printf '%s' "Jack & Lexie will be back tomorrow." > seg/e1.txt; printf '%s' "Subscribe so your dog never watches alone." > seg/e2.txt; printf '%s' "Made for dogs. Loved by their people." > seg/e3.txt
  ffmpeg -loglevel error -y -f lavfi -i "color=c=0x1F4E9A:s=${W}x${HT}:d=$2:r=$FPS" -vf "drawtext=fontfile='$FONT':textfile=seg/e1.txt:fontcolor=0xFFD23F:fontsize=84:x=(w-tw)/2:y=h/2-160,drawtext=fontfile='$FONT':textfile=seg/e2.txt:fontcolor=0xFFD23F:fontsize=60:x=(w-tw)/2:y=h/2-20,drawtext=fontfile='$FONTR':textfile=seg/e3.txt:fontcolor=0xFFF6D6:fontsize=40:x=(w-tw)/2:y=h/2+120,fade=t=in:st=0:d=0.5,fade=t=out:st=$(awk "BEGIN{print $2-2}"):d=2,format=yuv420p" $ENC "seg/$1.mp4"
}
# ---- timeline (name|kind|asset|dur|opt) ----
SHOTS="
001|push|S1|3
002|clip|V1|6
003|clip|V2|6
004|title|S3|5
010|card|1. Good Morning|2
011|clip|V3|6
012|push|S4|2
013|push|S5|10
014|clip|V4|5
015|push|S6|10
016|push|S7|17
017|clip|V5|6
018|push|S8|4
019|push|S9|8
020|card|2. The Walk|2
021|pan|S13|20|r
022|pan|S14|10|r
023|clip|V6|6
024|pan|S15|9|r
025|pan|S16|13|r
026|clip|V7|6
027|push|S17|4
028|push|S18|10
029|push|S19|10
030|card|3. The Park|2
031|clip|V8|5
032|push|S20|5
033|push|S21|8
034|push|S22|18
035|push|S23|7
036|push|S24|20
037|push|S25|7
038|clip|V9|5
039|push|S26|8
040|push|S27|10
041|push|S28|25
050|card|4. Snack Time|2
051|clip|V10|5
052|push|S29|8
053|push|S30|15
054|clip|V11|6
055|push|S31|6
056|push|S32|18
060|card|5. Heading Home|2
061|pan|S36|30|l
062|clip|V12|6
063|push|S33|2
064|push|S34|8
065|push|S35|12
070|card|6. Bedtime|2
071|clip|V13|8
072|push|S37|10
073|push|S38|12
074|push|S39|8
075|clip|V14|8
076|push|P9|4
077|end||8
"
: > seg/list.txt
echo "$SHOTS" | grep -v '^$' | while IFS='|' read -r n k a d o; do
  case $k in
    push) push $n $a.png $d;; pan) pan $n $a.png $d $o;; clip) clip $n $a.mp4 $d;;
    card) card $n "$a" $d;; title) title $n $a.png $d;; end) endcard $n $d;;
  esac
  echo "file '$n.mp4'" >> seg/list.txt; echo "seg $n done $(date +%T)"
done
ffmpeg -loglevel error -y -f concat -safe 0 -i seg/list.txt -c copy out/video.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 out/video.mp4
# ---- audio: music loop 8:00 + voiceover at 0:14 ----
ffmpeg -loglevel error -y -i src/music.mp3 -af "afade=t=in:st=0:d=0.5,afade=t=out:st=119:d=2" -ar 44100 seg/m.wav
ffmpeg -loglevel error -y -i seg/m.wav -i seg/m.wav -i seg/m.wav -i seg/m.wav -i seg/m.wav -filter_complex "[0:a][1:a]acrossfade=d=2:c1=tri:c2=tri[a];[a][2:a]acrossfade=d=2:c1=tri:c2=tri[b];[b][3:a]acrossfade=d=2:c1=tri:c2=tri[c];[c][4:a]acrossfade=d=2:c1=tri:c2=tri[d];[d]atrim=0:480,loudnorm=I=-19:TP=-2:LRA=7,volume=enable='between(t,13.5,29)':volume=0.45[m]" -map "[m]" -ar 44100 seg/music8.wav
ffmpeg -loglevel error -y -i seg/music8.wav -i src/vo.mp3 -filter_complex "[1:a]adelay=14000|14000,loudnorm=I=-16:TP=-1.5:LRA=7,volume=0.9[v];[0:a][v]amix=inputs=2:duration=first:normalize=0,afade=t=out:st=476:d=4[a]" -map "[a]" -ar 44100 seg/mix.wav
ffmpeg -loglevel error -y -i out/video.mp4 -i seg/mix.wav -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart out/episode.mp4
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height -of default=nw=1 out/episode.mp4; ls -la out/episode.mp4
curl -sS -f -o /dev/null -w "PUT %{http_code}\n" -X PUT -H "Content-Type: video/mp4" --data-binary @out/episode.mp4 "$UPLOAD_URL"
echo ALLDONE
