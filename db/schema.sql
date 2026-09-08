create extension if not exists pgcrypto;

create type incident_urgency as enum ('critical', 'high', 'standard');
create type incident_status as enum ('open', 'acknowledged', 'resolved');

create table incidents (
  id uuid primary key default gen_random_uuid(),
  transcript text not null,
  issue text not null,
  location text not null,
  owner text not null,
  urgency incident_urgency not null default 'standard',
  next_step text not null,
  status incident_status not null default 'open',
  spoken_text text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index incidents_status_created_idx on incidents (status, created_at desc);
create index incidents_location_idx on incidents (location);

create table users (
  id uuid primary key default gen_random_uuid(),
  email varchar(255) unique not null,
  created_at timestamptz not null default now()
);

create table rooms (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  name varchar(100) not null
);

create table devices (
  id varchar(100) primary key,
  room_id uuid references rooms(id) on delete set null,
  name varchar(100) not null,
  device_type varchar(50) not null,
  mqtt_topic varchar(255) not null,
  current_state jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create index devices_room_idx on devices (room_id);
