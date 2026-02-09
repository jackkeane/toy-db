#pragma once

#include "page.hpp"
#include "page_manager.hpp"
#include <memory>
#include <unordered_map>
#include <unordered_set>
#include <list>

namespace toydb {

/**
 * BufferPool - In-memory cache for pages with LRU eviction
 * 
 * Keeps frequently accessed pages in memory to reduce disk I/O
 */
class BufferPool {
public:
    explicit BufferPool(size_t capacity, PageManager* pm);
    ~BufferPool() = default;

    // Fetch page (from cache or disk)
    std::shared_ptr<Page> FetchPage(PageID page_id);
    
    // Mark page as dirty (needs to be written back)
    void MarkDirty(PageID page_id);
    
    // Flush all dirty pages
    void FlushDirty();
    
    // Get cache hit rate (for debugging/stats)
    double GetHitRate() const {
        size_t total = cache_hits_ + cache_misses_;
        return total > 0 ? static_cast<double>(cache_hits_) / total : 0.0;
    }

private:
    size_t capacity_;
    PageManager* page_manager_;
    
    // LRU tracking: most recently used at front
    std::list<PageID> lru_list_;
    
    // Cache: page_id -> (page, iterator to position in LRU list)
    std::unordered_map<PageID, std::pair<std::shared_ptr<Page>, std::list<PageID>::iterator>> cache_;
    
    // Dirty pages set
    std::unordered_set<PageID> dirty_pages_;
    
    // Stats
    size_t cache_hits_ = 0;
    size_t cache_misses_ = 0;
    
    // Evict least recently used page
    void Evict();
    
    // Move page to front of LRU list (mark as recently used)
    void Touch(PageID page_id);
};

} // namespace toydb
