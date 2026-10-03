#!/bin/bash
# "Jack & Lexie's Big Day Out" v2 - fully animated, no still pans.
# Every shot is a generated clip; long holds are filled by ping-pong or forward looping.
set -eu
cd /home/user; mkdir -p src2 seg2 out
H=https://d8j0ntlcm91z4.cloudfront.net/user_3J8Na3IQJEUtBerYQQOxXHpH4Y4
W=1920; HT=1080; FPS=24
FONT=$(find /usr/share/fonts -iname "DejaVuSans-Bold.ttf" -print -quit 2>/dev/null || true)
FONTR=$(find /usr/share/fonts -iname "DejaVuSans.ttf" -print -quit 2>/dev/null || true)
echo "font=$FONT"
ENC="-c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -r $FPS -an"

# ---- source clips: new Wan 3.0 animations (SHOT -> url basename) ----
cat > src2/map.txt <<'MAP'
S1 hf_20260914_220405_b94ec942-83de-4e9d-b1d5-0c65507d3cba.mp4
S7 hf_20260914_220405_cfb14b6b-2c6b-42b8-b6f9-8d6f50a879f9.mp4
S13 hf_20260914_220405_982380cd-3265-47f7-8e86-39b150d73b6e.mp4
S24 hf_20260914_220406_2b88cd3d-d0b5-4ac6-b08e-b8b157f916e9.mp4
S28 hf_20260914_220405_388e05b1-3f66-49ff-b4fd-e916c9a48df3.mp4
S36 hf_20260914_220405_d2fb6e0d-0d07-427e-be43-45287290ec3d.mp4
S9 hf_20260914_220641_1043aaa6-e6f6-4187-93c9-e2c9057cb665.mp4
S16 hf_20260914_220641_9587c746-4598-4b79-bf87-56910508de15.mp4
S18 hf_20260914_220641_3ac5310a-6b15-4e8c-b8c3-fc92b61c3e20.mp4
S19 hf_20260914_220641_2c5b76a0-aef7-44be-8e00-40621c43bb8c.mp4
S23 hf_20260914_220743_4c9534f2-dd3a-46c8-912b-ca64223353f8.mp4
S25 hf_20260914_220743_685ffa78-9758-4476-89aa-917f35513f97.mp4
S5 hf_20260914_220948_8badc72a-16ad-46af-a937-9f256fd7584d.mp4
S14 hf_20260914_220948_ee5e563c-cc60-4a96-8bcc-fa04dbd2d71a.mp4
S21 hf_20260914_220948_580f0887-0bdf-4e7f-8c2f-3bb5c81a086a.mp4
S22 hf_20260914_221040_18f0a540-7fc2-45a1-9321-a95d2db59b66.mp4
S27 hf_20260914_221039_64cd9a72-7e72-4e6a-94e1-19f3864f51a3.mp4
S30 hf_20260914_221039_c57cc9df-0bdb-4cfe-8bb2-a15a5fdb556d.mp4
S32 hf_20260914_221256_edd37943-8613-4fb9-b51f-8079259fde85.mp4
S34 hf_20260914_221256_7f90fdc6-319c-4140-b1d6-83f68e2dc4dd.mp4
S35 hf_20260914_221408_0e853fe5-d197-450a-a712-c79f88e218ac.mp4
S38 hf_20260914_221408_bb1852fc-911c-47ad-b439-6b7887c5d762.mp4
S39 hf_20260914_221324_2199a0ee-a5f1-4fe7-8f5f-c50976da0db0.mp4
V1 hf_20260913_233955_e8237d0d-de03-4eaa-8493-cb39f5d8394e.mp4
V2 hf_20260913_233955_6617ace6-e3cf-4900-b30b-a07d9c600e2f.mp4
V3 hf_20260913_233955_610baed5-2bf3-4f6b-8804-bdc16b77fe8f.mp4
V4 hf_20260913_233724_b2574d33-efb3-4d55-ab02-abc927693106.mp4
V5 hf_20260913_234335_9999499b-86be-43a6-97cb-47888937a055.mp4
V6 hf_20260913_234335_744d6fd6-a141-4f03-a4c0-a4394939041a.mp4
V7 hf_20260913_233724_0e5e154b-bbbd-44bf-8d2f-b45b9b34285b.mp4
V8 hf_20260913_233724_09303d46-1b50-4d30-a184-c516b7bc9ede.mp4
V9 hf_20260913_233725_2eb822ef-6aba-4e2c-9270-6e1c907207ea.mp4
V10 hf_20260913_233724_db6904af-35b4-413d-9c40-98a15e7b5057.mp4
V11 hf_20260913_234335_6a288650-b029-4ac6-8f58-f9ae6ea0761c.mp4
V12 hf_20260913_233724_6e023b93-07af-43f4-9c2a-9d6cf650207f.mp4
V13 hf_20260913_234037_a82b4693-891f-4651-9564-2cd02602a63a.mp4
V14 hf_20260913_234037_409d5903-64e4-472c-991a-d763180789df.mp4
MAP
# extra clips appended at run time by the caller (EXTRA_MAP), e.g. S32/S34/S35/S38/S39
if [ -n "${EXTRA_MAP:-}" ]; then printf "%s\n" "$EXTRA_MAP" >> src2/map.txt; fi
: > src2/dl.txt
while read -r k f; do [ -z "$k" ] && continue; [ -f "src2/$k.mp4" ] || echo "$H/$f src2/$k.mp4" >> src2/dl.txt; done < src2/map.txt
echo "downloading $(wc -l < src2/dl.txt)"
xargs -P 8 -n 2 sh -c 'curl -sf -m 600 -L -o "$1" "$0" || echo "DLFAIL $0"' < src2/dl.txt
for k in $(awk '{print $1}' src2/map.txt); do ffprobe -v error "src2/$k.mp4" >/dev/null 2>&1 || echo "BAD $k"; done
echo "sources ok: $(ls src2/*.mp4 | wc -l)"

norm(){ # normalise any source clip to 1920x1080 24fps: $1 shot
  [ -f "seg2/n_$1.mp4" ] && return 0
  ffmpeg -nostdin -loglevel error -y -i "src2/$1.mp4" -vf "scale=$W:$HT:force_original_aspect_ratio=increase,crop=$W:$HT,fps=$FPS,format=yuv420p" $ENC "seg2/n_$1.mp4"
}
pingpong(){ # forward + reverse: $1 shot
  [ -f "seg2/p_$1.mp4" ] && return 0
  ffmpeg -nostdin -loglevel error -y -i "seg2/n_$1.mp4" -filter_complex "[0:v]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1[o]" -map "[o]" $ENC "seg2/p_$1.mp4"
}
shot(){ # $1 outname $2 shot $3 dur $4 mode(direct|pp|fwd)
  n=$1; k=$2; d=$3; m=$4
  [ -f "seg2/$n.mp4" ] && { echo "skip $n"; return 0; }
  norm "$k"
  case $m in
    direct) ffmpeg -nostdin -loglevel error -y -i "seg2/n_$k.mp4" -t $d $ENC "seg2/$n.mp4";;
    pp) pingpong "$k"; ffmpeg -nostdin -loglevel error -y -stream_loop 20 -i "seg2/p_$k.mp4" -t $d $ENC "seg2/$n.mp4";;
    fwd) ffmpeg -nostdin -loglevel error -y -stream_loop 20 -i "seg2/n_$k.mp4" -t $d $ENC "seg2/$n.mp4";;
  esac
  echo "shot $n ($k $m ${d}s) $(date +%T)"
}
card(){ printf '%s' "$2" > seg2/$1.txt
  ffmpeg -nostdin -loglevel error -y -f lavfi -i "color=c=0x1F4E9A:s=${W}x${HT}:d=$3:r=$FPS" -vf "drawtext=fontfile='$FONT':textfile=seg2/$1.txt:fontcolor=0xFFD23F:fontsize=96:x=(w-tw)/2:y=(h-th)/2,fade=t=in:st=0:d=0.3,fade=t=out:st=$(awk "BEGIN{print $3-0.3}"):d=0.3,format=yuv420p" $ENC "seg2/$1.mp4"; echo "card $1"; }
title(){ # title band over a ping-ponged continuation of V2
  norm V2; pingpong V2
  printf '%s' "Jack & Lexie's Big Day Out" > seg2/t1.txt; printf '%s' "Dog TV in colors your dog can see" > seg2/t2.txt
  ffmpeg -nostdin -loglevel error -y -stream_loop 20 -i "seg2/p_V2.mp4" -t $2 -vf "drawbox=x=0:y=ih-360:w=iw:h=360:color=0x1F4E9A@0.88:t=fill,drawtext=fontfile='$FONT':textfile=seg2/t1.txt:fontcolor=0xFFD23F:fontsize=100:x=(w-tw)/2:y=h-300,drawtext=fontfile='$FONTR':textfile=seg2/t2.txt:fontcolor=0xFFF6D6:fontsize=44:x=(w-tw)/2:y=h-150,format=yuv420p" $ENC "seg2/$1.mp4"; echo "title $1"; }
endcard(){ printf '%s' "Jack & Lexie will be back tomorrow." > seg2/e1.txt; printf '%s' "Subscribe so your dog never watches alone." > seg2/e2.txt; printf '%s' "Made for dogs. Loved by their people." > seg2/e3.txt
  ffmpeg -nostdin -loglevel error -y -f lavfi -i "color=c=0x1F4E9A:s=${W}x${HT}:d=$2:r=$FPS" -vf "drawtext=fontfile='$FONT':textfile=seg2/e1.txt:fontcolor=0xFFD23F:fontsize=84:x=(w-tw)/2:y=h/2-160,drawtext=fontfile='$FONT':textfile=seg2/e2.txt:fontcolor=0xFFD23F:fontsize=60:x=(w-tw)/2:y=h/2-20,drawtext=fontfile='$FONTR':textfile=seg2/e3.txt:fontcolor=0xFFF6D6:fontsize=40:x=(w-tw)/2:y=h/2+120,fade=t=in:st=0:d=0.5,fade=t=out:st=$(awk "BEGIN{print $2-2}"):d=2,format=yuv420p" $ENC "seg2/$1.mp4"; echo "endcard $1"; }

TL="
001|gen|S1|3|direct
002|gen|V1|6|direct
003|gen|V2|6|direct
004|title|V2|5|pp
010|card|1. Good Morning|2|-
011|gen|V3|8|pp
013|gen|S5|10|direct
014|gen|V4|15|pp
016|gen|S7|17|pp
017|gen|V5|10|pp
019|gen|S9|8|direct
020|card|2. The Walk|2|-
021|gen|S13|20|fwd
022|gen|S14|10|direct
023|gen|V6|15|pp
025|gen|S16|13|fwd
026|gen|V7|10|pp
028|gen|S18|10|direct
029|gen|S19|10|direct
030|card|3. The Park|2|-
031|gen|V8|10|pp
033|gen|S21|8|direct
034|gen|S22|18|pp
035|gen|S23|7|direct
036|gen|S24|20|pp
037|gen|S25|7|direct
038|gen|V9|13|pp
040|gen|S27|10|direct
041|gen|S28|25|pp
050|card|4. Snack Time|2|-
051|gen|V10|13|pp
053|gen|S30|15|pp
054|gen|V11|12|pp
056|gen|S32|18|pp
060|card|5. Heading Home|2|-
061|gen|S36|30|fwd
062|gen|V12|8|pp
064|gen|S34|8|direct
065|gen|S35|12|direct
070|card|6. Bedtime|2|-
071|gen|V13|18|pp
073|gen|S38|12|direct
074|gen|S39|8|direct
075|gen|V14|12|pp
077|end||8|-
"
J=$(nproc); [ "$J" -gt 5 ] && J=5
: > seg2/list.txt
while IFS='|' read -r n k a d m; do
  [ -z "$n" ] && continue
  echo "file '$n.mp4'" >> seg2/list.txt
  while [ "$(jobs -rp | wc -l)" -ge "$J" ]; do sleep 1; done
  case $k in
    gen)   ( shot "$n" "$a" "$d" "$m" ) & ;;
    card)  ( card "$n" "$a" "$d" ) & ;;
    title) ( title "$n" "$d" ) & ;;
    end)   ( endcard "$n" "$d" ) & ;;
  esac
done <<< "$TL"
wait
MISS=0; for f in $(sed "s/file '\(.*\)'/\1/" seg2/list.txt); do [ -f "seg2/$f" ] || { echo "MISSING $f"; MISS=1; }; done; [ $MISS = 0 ]
echo "segments done $(date +%T)"
ffmpeg -nostdin -loglevel error -y -f concat -safe 0 -i seg2/list.txt -c copy out/video2.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 out/video2.mp4
# audio identical to v1: MiniMax bed looped to 8:00, Benji VO at 0:14
if [ ! -f seg2/mix.wav ]; then
  [ -f src2/music.mp3 ] || curl -sf -L -o src2/music.mp3 "https://gcdn.picsart.com/editing-temp/768a5dae-ae9c-42e9-8403-e572dedb6a1b.mp3"
  [ -f src2/vo.mp3 ] || curl -sf -L -o src2/vo.mp3 "$H/hf_20260913_235512_e095e732-c930-4ed4-b8b1-9b07cf15687e.mp3"
  ffmpeg -nostdin -loglevel error -y -i src2/music.mp3 -af "afade=t=in:st=0:d=0.5,afade=t=out:st=119:d=2" -ar 44100 seg2/m.wav
  ffmpeg -nostdin -loglevel error -y -i seg2/m.wav -i seg2/m.wav -i seg2/m.wav -i seg2/m.wav -i seg2/m.wav -filter_complex "[0:a][1:a]acrossfade=d=2:c1=tri:c2=tri[a];[a][2:a]acrossfade=d=2:c1=tri:c2=tri[b];[b][3:a]acrossfade=d=2:c1=tri:c2=tri[c];[c][4:a]acrossfade=d=2:c1=tri:c2=tri[d];[d]atrim=0:480,loudnorm=I=-19:TP=-2:LRA=7,volume=enable='between(t,13.5,29)':volume=0.45[m]" -map "[m]" -ar 44100 seg2/music8.wav
  ffmpeg -nostdin -loglevel error -y -i seg2/music8.wav -i src2/vo.mp3 -filter_complex "[1:a]adelay=14000|14000,loudnorm=I=-16:TP=-1.5:LRA=7,volume=0.9[v];[0:a][v]amix=inputs=2:duration=first:normalize=0,afade=t=out:st=476:d=4[a]" -map "[a]" -ar 44100 seg2/mix.wav
fi
ffmpeg -nostdin -loglevel error -y -i out/video2.mp4 -i seg2/mix.wav -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart out/episode2.mp4
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height -of default=nw=1 out/episode2.mp4; ls -la out/episode2.mp4
if [ -n "${UPLOAD_URL:-}" ]; then curl -sS -f -o /dev/null -w "PUT %{http_code}\n" -X PUT -H "Content-Type: video/mp4" --data-binary @out/episode2.mp4 "$UPLOAD_URL"; fi
echo ALLDONE
