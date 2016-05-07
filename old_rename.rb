#!/usr/bin/ruby

require 'exif'
require 'fileutils'
require 'date'

MIXDIR = "mix"
FileUtils.rm_rf MIXDIR
FileUtils.makedirs MIXDIR

[ "anne", "fredg", "kim", "mat", "sophie" ].each do |author|
  Dir.glob("#{author}/**/*.JPG").sort.each do |filename|
    exif = Exif.new(filename)
    exif.each_entry do |k,v| puts "#{k} -> #{v}" end

    time = DateTime.strptime( exif["Date and Time \(Original\)"], '%Y:%m:%d %H:%M:%S')
    puts  "ln -s ../#{filename} #{MIXDIR}/#{time.strftime '%Y%m%d_%H%M%S'}_#{author}_#{File.basename(filename)}"
  end
end
