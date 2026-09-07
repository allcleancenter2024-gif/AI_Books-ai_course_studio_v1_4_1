import express from 'express';
import mongoose from 'mongoose';
import { PrismaClient } from '@prisma/client';

const app = express();
const prisma = new PrismaClient();
const rawSchema = new mongoose.Schema({}, { strict: false, collection: 'raw_sources' });
const RawSource = mongoose.model('RawSource', rawSchema);

async function connectDatabases() {
  await Promise.all([prisma.$connect(), mongoose.connect(process.env.MONGODB_URI)]);
}

app.get('/health', async (_req, res) => {
  try {
    const [postgres, mongo] = await Promise.all([prisma.$queryRaw`SELECT 1 AS ok`, mongoose.connection.db.admin().ping()]);
    res.json({ ok: true, postgres: Boolean(postgres), mongodb: mongo.ok === 1 });
  } catch (error) { res.status(503).json({ ok: false, error: error.message }); }
});

app.get('/sources', async (_req, res, next) => {
  try { res.json(await RawSource.find().sort({ collectedAt: -1 }).limit(100).lean()); }
  catch (error) { next(error); }
});
app.use((error, _req, res, _next) => res.status(500).json({ ok: false, error: error.message }));

connectDatabases().then(() => app.listen(process.env.PORT || 3000, '0.0.0.0', () => console.log('app-api ready')))
  .catch((error) => { console.error('database connection failed', error); process.exit(1); });
