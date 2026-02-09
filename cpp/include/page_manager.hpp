#pragma once

#include "page.hpp"
#include <string>
#include <fstream>
#include <unordered_map>
#include <memory>

namespace toydb {

/**
 * PageManager - Manages page lifecycle and disk I/O
 * 
 * Responsibilities:
 * - Allocate new pages
 * - Read/write pages to disk
 * - Track page metadata
 */
class PageManager {
public:
    explicit PageManager(const std::string& db_file);
    ~PageManager();

    // Allocate a new page
    PageID AllocatePage();
    
    // Read page from disk
    std::shared_ptr<Page> ReadPage(PageID page_id);
    
    // Write page to disk
    bool WritePage(const std::shared_ptr<Page>& page);
    
    // Flush all dirty pages to disk
    void FlushAll();
    
    // Get total number of pages
    size_t GetNumPages() const { return next_page_id_; }

private:
    std::string db_file_;
    std::fstream file_;
    PageID next_page_id_;  // Next available page ID
    
    // Simple cache: page_id -> Page
    std::unordered_map<PageID, std::shared_ptr<Page>> cache_;
    
    // Open/create database file
    void OpenOrCreateFile();
};

} // namespace toydb
