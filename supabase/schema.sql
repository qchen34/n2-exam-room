-- ============================================================
--  N2 試験室：端末同期用スキーマ
--  使い方：Supabase ダッシュボード → SQL Editor → New query →
--         このファイルの中身を貼り付けて Run（1 回だけ）
-- ============================================================

-- 1) 学習記録を 1 行 = 1 端末グループで持つ表
create table if not exists public.sync_state (
  code        text primary key,                 -- 同期コード（8 桁）
  sync_key    text not null,                    -- 鍵（40 桁）。これが無いと読み書きできない
  data        jsonb not null default '{}'::jsonb,
  updated_at  timestamptz not null default now()
);

-- 2) 直接アクセスは全拒否。触れるのは下の 2 つの関数だけ
alter table public.sync_state enable row level security;
revoke all on public.sync_state from anon, authenticated;

-- 3) 読み取り：コード + 鍵が一致したときだけ data を返す
create or replace function public.state_get(p_code text, p_key text)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare d jsonb;
begin
  select data into d
    from sync_state
   where code = p_code and sync_key = p_key;
  return d;
end;
$$;

-- 4) 書き込み：初回は insert、以降は鍵が一致しないと更新しない
create or replace function public.state_put(p_code text, p_key text, p_data jsonb)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
begin
  if octet_length(p_data::text) > 3000000 then
    raise exception 'PAYLOAD_TOO_LARGE';
  end if;

  insert into sync_state (code, sync_key, data, updated_at)
  values (p_code, p_key, p_data, now())
  on conflict (code) do update
     set data = excluded.data, updated_at = now()
   where sync_state.sync_key = p_key;

  -- 鍵違いで更新されなかった場合は false を返す
  return coalesce((select sync_key = p_key from sync_state where code = p_code), false);
end;
$$;

-- 5) 匿名キー（anon）からこの 2 つだけ呼べるようにする
grant execute on function public.state_get(text, text) to anon;
grant execute on function public.state_put(text, text, jsonb) to anon;

-- 確認用（0 行なら OK）
-- select code, updated_at from public.sync_state;

-- ============================================================
--  聴解音声の置き場（public バケット）
--  これも SQL Editor で 1 回だけ実行。ダッシュボードから
--  Storage → New bucket で作る場合は、名前 audio・Public を on にすれば同じ。
-- ============================================================
insert into storage.buckets (id, name, public)
values ('audio', 'audio', true)
on conflict (id) do nothing;

-- 公開バケットは /storage/v1/object/public/audio/<file> で誰でも読める。
-- バケット内の一覧（list）は既定で拒否。URL を知っている人だけが取得できる。
-- 音声は著作物なので、この URL を公開ページに貼らないこと。
