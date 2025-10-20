BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "school" (
	"school_id"	INTEGER,
	"school_name"	TEXT NOT NULL,
	PRIMARY KEY("school_id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "round_robin_race" (
	"event_id"	INTEGER,
	"race"	INTEGER,
	"round"	INTEGER,
	"car_lane_1"	INTEGER,
	"car_lane_2"	INTEGER,
	"car_lane_1_points"	INTEGER,
	"car_lane_2_points"	INTEGER,
	FOREIGN KEY("car_lane_1") REFERENCES "car"("car_id"),
	FOREIGN KEY("event_id") REFERENCES "event"("event_id"),
	PRIMARY KEY("event_id","race"),
	FOREIGN KEY("car_lane_2") REFERENCES "car"("car_id")
);
CREATE TABLE IF NOT EXISTS "event" (
	"event_id"	INTEGER,
	"event_date"	TEXT DEFAULT CURRENT_TIMESTAMP,
	"event_name"	TEXT,
	PRIMARY KEY("event_id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "car" (
	"event_id"	INTEGER,
	"car_id"	INTEGER,
	"school_id"	INTEGER,
	"car_name"	TEXT,
	"car_scruitineered"	INTEGER CHECK("car_scruitineered" IN (0, 1)),
	"present_round_robin"	INTEGER CHECK("present_round_robin" IN (0, 1)),
	"present_knockout"	INTEGER CHECK("present_knockout" IN (0, 1)),
	PRIMARY KEY("car_id","event_id"),
	FOREIGN KEY("event_id") REFERENCES "event"("event_id")
);
COMMIT;
