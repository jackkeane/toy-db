#include "buffer_pool.hpp"
#include <unordered_set>

namespace toydb {

BufferPool::BufferPool(size_t capacity, PageManager* pm)
    : capacity_(capacity), page_manager_(pm) {}

std::shared_ptr<Page> BufferPool::FetchPage(PageID page_id) {
    // Check if page is in cache
    auto it = cache_.find(page_id);
    if (it != cache_.end()) {
        cache_hits_++;
        Touch(page_id);
        return it->second.first;
    }
    
    cache_misses_++;
    
    // Page not in cache, need to load from disk
    // If cache is full, evict LRU page
    if (cache_.size() >= capacity_) {
        Evict();
    }
    
    // Read page from disk
    auto page = page_manager_->ReadPage(page_id);
    if (!page) {
        return nullptr;
    }
    
    // Add to cache
    lru_list_.push_front(page_id);
    cache_[page_id] = {page, lru_list_.begin()};
    
    return page;
}

void BufferPool::MarkDirty(PageID page_id) {
    dirty_pages_.insert(page_id);
}

void BufferPool::FlushDirty() {
    for (PageID page_id : dirty_pages_) {
        auto it = cache_.find(page_id);
        if (it != cache_.end()) {
            page_manager_->WritePage(it->second.first);
        }
    }
    dirty_pages_.clear();
}

void BufferPool::Evict() {
    if (lru_list_.empty()) {
        return;
    }
    
    // Get least recently used page (back of list)
    PageID evict_id = lru_list_.back();
    
    // If dirty, flush to disk
    if (dirty_pages_.count(evict_id)) {
        auto it = cache_.find(evict_id);
        if (it != cache_.end()) {
            page_manager_->WritePage(it->second.first);
        }
        dirty_pages_.erase(evict_id);
    }
    
    // Remove from cache
    cache_.erase(evict_id);
    lru_list_.pop_back();
}

void BufferPool::Touch(PageID page_id) {
    auto it = cache_.find(page_id);
    if (it == cache_.end()) {
        return;
    }
    
    // Move to front of LRU list
    lru_list_.erase(it->second.second);
    lru_list_.push_front(page_id);
    it->second.second = lru_list_.begin();
}

} // namespace toydb
