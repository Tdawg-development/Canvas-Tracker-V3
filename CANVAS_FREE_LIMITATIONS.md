# Canvas Free for Teachers - Limitations & Adaptations

## Overview
Canvas Tracker V3 is designed to work with **Canvas Free for Teachers** accounts, which have significant API limitations compared to paid Canvas instances.

## Canvas Free Limitations

### API Rate Limits
- **100 requests per hour** (vs 3000+ for paid accounts)
- **No webhooks** - must use polling for real-time updates
- **Limited concurrent requests** - max 2 simultaneous requests recommended
- **Smaller batch sizes** - max 3 items per batch to avoid timeouts

### Endpoint Restrictions
**Available Endpoints:**
- ✅ `GET /courses` - List courses
- ✅ `GET /courses/:id` - Get course details
- ✅ `GET /courses/:id/users` - Get course students
- ✅ `GET /courses/:id/assignments` - Get course assignments
- ✅ `GET /courses/:id/assignments/:id/submissions` - Get submissions

**Limited/Unavailable:**
- ❌ Advanced analytics endpoints
- ❌ Bulk operations
- ❌ Real-time notifications
- ❌ Administrative APIs
- ❌ SIS integration endpoints

### Data Limitations
- **Pagination limits** - typically 100 items per page maximum
- **Simplified data** - some fields may be unavailable
- **No real-time sync** - data freshness depends on polling interval
- **Limited historical data** - access to recent data only

## Our Adaptations

### CanvasFreeAdapter
- **Intelligent batching** - processes requests in small, spaced batches
- **Rate limit management** - automatically respects API quotas
- **Request queuing** - prevents concurrent request overload
- **Graceful fallbacks** - estimates data when API calls would be excessive

### Curriculum Strategy
- **Small curricula** - recommend 5 or fewer courses per curriculum
- **Conservative sync** - 15+ minute intervals to preserve API quota
- **Efficient queries** - single API calls include multiple data points
- **Local caching** - minimize repeated API calls

### User Experience
- **Transparent limitations** - clearly communicate Canvas Free constraints
- **Realistic expectations** - set appropriate sync frequencies
- **Manual refresh options** - allow user-initiated updates
- **Progress indicators** - show API usage and remaining quota

## Recommendations

### For Curriculum Setup
1. **Keep it small** - limit to 5 courses per curriculum maximum
2. **Plan timing** - schedule syncs during off-peak hours
3. **Monitor usage** - track API calls to avoid hitting limits
4. **Cache locally** - store frequently accessed data

### For Development
1. **Conservative defaults** - assume Canvas Free limitations
2. **Graceful degradation** - handle missing data elegantly
3. **User communication** - explain limitations clearly
4. **Testing** - always test against Canvas Free constraints

## Migration Path
If upgrading to paid Canvas later:
1. Update `CANVAS_ACCOUNT_TYPE=paid` in `.env`
2. Increase `CANVAS_RATE_LIMIT_REQUESTS_PER_HOUR=3000`
3. Enable additional API endpoints as needed
4. Reduce polling intervals for more real-time data

## Technical Implementation

### Environment Variables
```
CANVAS_ACCOUNT_TYPE=free
CANVAS_RATE_LIMIT_REQUESTS_PER_HOUR=100
CANVAS_MAX_CONCURRENT_REQUESTS=2
CANVAS_BATCH_SIZE_LIMIT=3
```

### Code Usage
```typescript
// Use CanvasFreeAdapter instead of direct Canvas API calls
const adapter = new CanvasFreeAdapter(canvasConfig);

// All methods return limitations info
const { courses, limitations } = await adapter.getCurriculumData(curriculum);

// Monitor API usage
const usage = adapter.getApiUsageStatus();
console.log(`API Usage: ${usage.percentageUsed}%`);
```

This approach ensures Canvas Tracker V3 works reliably within Canvas Free constraints while providing clear feedback about limitations to users.