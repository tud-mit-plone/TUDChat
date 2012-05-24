/*
 * hyperlink replaces all text links within a passed text string to html links
 * Note: it's better to do this as a one time filter when passing the data into the database
 * rather than filtering every time the UI is rendered. But here it is:
 * @param {string} txt, the text to format
 * @return {string} the newly formatted text
*/
var hyperlink = function(txt) {
    var regUrl = /(^|[^>\"\/])(http[s]{0,1}:\/\/|www\.)(?:[^\"])\S*([\s\)\!]|$)/gi;
    /* 
    Regex breakdown for regUrl:
    globally search for URLs within text that are not already attributes of tags
    /^|[^>\"\/]/ match start of txt or a character that is not a quote or > (avoid matching a/img links: <a href="http://...">http://...</a>) and do not match http://www as a duplicate of matching http://
    /(http:\/\/|www\.)/ can begin with 'http://' or 'wwww.'
    /\S*([\s\)\!]|$)/ match all non-whitespace characters until reach a space, closing parenthetical, exclamation or end of text
    
    // match captures the following, attribed to values in the replace function:
    // $1 = $href:     full match (link plus first and last char)
    // $2 = $start:    first character (not a quote, not part of the URL)
    // $3 = $urlStart: 'http://' or 'www.'
    // $4 = $end:      concluding character (' ',')','!','')
    // $5 = $pos:      position of match in txt
    // $6 = $txt:      full txt parsed
    */
    var aTag = '<a href="{0}" target=\'_blank\'>{1}</a>',
          // capture trailing non-url, non-space characters from the end of a string.
          regUrlTail = /[\!\]\.\?]+$/g, // removed \)
          txt = txt.replace(regUrl, function($href,$start,$urlStart,$end,$pos,$txt){
        if(!$href) // no match
            return ''; // nothing to replace
        if($start) // a character (not just the begining of the txt)
            $href=$href.substr(1,$href.length-1); // remove start character
        if($end) // end will be one character but might include an extra trailing characters (such as '!!!')
            $href=$href.substr(0,$href.length-1); // remove end character
        // capture trailing non-space, non-url characters (matched as part of \S*
        var trail = $href.match(regUrlTail);
        if(trail) $href = $href.replace(regUrlTail,''); // strip trail from link
        if($href.search(/http/i)!=0) $href = 'http://' + $href; // must start with http
        var lnk = ellipsis($href,100); // keep visible link short
        return $start + String.format(aTag,stripMal($href),stripMal(lnk)) + (trail?trail[0]:'') + $end; // add the start and trail+end back on
    });
    return txt;
};

/*
 * stripMal strips all malicious script injection code
 * @param {string} txt The text to filter
 * @return {string} text stripped of any malicious script declaraion ('javascript:', 'vbscript:', etc...)
 */
var stripMal = function(txt) {
    return txt.replace(/(?:java|vb)?(?:script|data):/gi,'');
};

/**
 * shorten text, adding '...' in place of excessive characters
 * @param {string} txt The string to shorten
 * @param {int} l The length to truncate
 */
var ellipsis = function(txt,l) {
    l = l || 20; // default to 20
    return txt.length > l ? txt.slice(0, l - 3) + '...' : txt;
};

String.format = function() {
  var s = arguments[0];
  for (var i = 0; i < arguments.length - 1; i++) {       
    var reg = new RegExp("\\{" + i + "\\}", "gm");             
    s = s.replace(reg, arguments[i + 1]);
  }

  return s;
}