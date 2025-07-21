// prevents duplcates with generic_events_scheduler.py

db.events.createIndex(
    {
        "originatingServerId": 1,
        "timestamp": 1,
        "type": 1,
        "originatingEventId": 1,
	"thisId": 1
    },
    {
        unique: true,
        name: "unique_event_compound_idx",
	background: true 
    }
)

-----------------------------


// Mongo Shell Script to Clean Duplicates
const collectionName = "events";

// Aggregation pipeline to find duplicate documents
const pipeline = [
  {
    $group: {
      _id: {
        originatingServerId: "$originatingServerId",
        timestamp: "$timestamp",
        cameraId: "$cameraId",
        type: "$type",
        thisId: "$thisId",
        linkedEventId: "$linkedEventId"
      },
      uniqueIds: { $addToSet: "$_id" },
      count: { $sum: 1 }
    }
  },
  {
    $match: {
      count: { $gt: 1 }
    }
  }
];

// Run the aggregation
print(`Finding duplicate groups in '${collectionName}'...`);
const duplicates = db.getCollection(collectionName).aggregate(pipeline).toArray();
print(`Found ${duplicates.length} groups of duplicate events.`);

if (duplicates.length > 0) {
  print("Starting cleanup process...\n");
  let totalDocsToRemove = 0;

  duplicates.forEach(doc => {
    // Keep one _id, delete the rest
    const idsToRemove = doc.uniqueIds.slice(1); // keep first, delete rest
    totalDocsToRemove += idsToRemove.length;

    print(`- Group Key: ${EJSON.stringify(doc._id)}`);
    print(`  Found ${doc.count} duplicates. Keeping one, removing ${idsToRemove.length}.`);

    const result = db.getCollection(collectionName).deleteMany({
      _id: { $in: idsToRemove }
    });

    print(`  Deletion result: ${result.deletedCount} document(s) removed.\n`);
  });

  print(`--- Cleanup Complete ---`);
  print(`Total documents removed: ${totalDocsToRemove}`);
} else {
  print("No duplicate documents found. Your data is clean.");
}
