CREATE TABLE profiles (
  id PRIMARY KEY,
  mal_name,
  xp INTEGER,
  level INTEGER
);
CREATE TABLE stats (
  id PRIMARY KEY,
  days,
  completed,
  meanscore
);
CREATE TABLE levels (
  level INTEGER PRIMARY KEY,
  minxp INTEGER,
  maxxp INTEGER
);
