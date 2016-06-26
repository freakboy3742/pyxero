from __future__ import unicode_literals


# exceptions.py

bad_request_text = """<ApiException xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <ErrorNumber>10</ErrorNumber>
  <Type>ValidationException</Type>
  <Message>A validation exception occurred</Message>
  <Elements>
    <DataContractBase xsi:type="Invoice">
      <ValidationErrors>
        <ValidationError>
          <Message>One or more line items must be specified</Message>
        </ValidationError>
        <ValidationError>
          <Message>Invoice not of valid status for creation</Message>
        </ValidationError>
        <ValidationError>
          <Message>A Contact must be specified for this type of transaction</Message>
        </ValidationError>
      </ValidationErrors>
      <Warnings />
      <Date>2013-04-29T00:00:00</Date>
      <DueDate>2013-04-29T00:00:00</DueDate>
      <BrandingThemeID xsi:nil="true" />
      <Status>PAID</Status>
      <LineAmountTypes>Exclusive</LineAmountTypes>
      <LineItems />
      <SubTotal>18.00</SubTotal>
      <TotalTax>1.05</TotalTax>
      <Total>19.05</Total>
      <UpdatedDateUTC xsi:nil="true" />
      <CurrencyCode>AUD</CurrencyCode>
      <FullyPaidOnDate xsi:nil="true" />
      <Type>ACCREC</Type>
      <InvoiceID>00000000-0000-0000-0000-000000000000</InvoiceID>
      <Reference>Order # 123456</Reference>
      <Payments />
      <CreditNotes />
      <AmountDue>0.00</AmountDue>
      <AmountPaid>19.05</AmountPaid>
      <AmountCredited xsi:nil="true" />
      <SentToContact xsi:nil="true" />
      <CurrencyRate xsi:nil="true" />
      <TotalDiscount xsi:nil="true" />
      <HasAttachments xsi:nil="true" />
      <Attachments />
    </DataContractBase>
  </Elements>
</ApiException>"""

not_implemented_text = """<ApiException xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <ErrorNumber>20</ErrorNumber>
    <Type>ApiMethodNotImplementedException</Type>
    <Message>The Api Method called is not implemented</Message>
</ApiException>"""


# manager.py

unicode_content_text = u"""<Response xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <Id>dbb54b2b-8fdb-4277-ad03-2df50ce760fa</Id>
  <Status>OK</Status>
  <ProviderName>TradesCloud</ProviderName>
  <DateTimeUTC>2013-05-31T06:07:35.3732465Z</DateTimeUTC>
  <Contacts>
    <Contact>
      <ContactID>755f1475-d255-43a8-bedc-5ea7fd26c71f</ContactID>
      <ContactStatus>ACTIVE</ContactStatus>
      <Name>Yarra Transport</Name>
      <FirstName>John</FirstName>
      <LastName>S\xfcrname</LastName>
      <EmailAddress>rayong@yarratransport.co</EmailAddress>
      <Addresses>
        <Address>
          <AddressType>STREET</AddressType>
        </Address>
        <Address>
          <AddressType>POBOX</AddressType>
          <AddressLine1>P O Box 5678</AddressLine1>
          <City>Melbourne</City>
          <PostalCode>3133</PostalCode>
        </Address>
      </Addresses>
      <Phones>
        <Phone>
          <PhoneType>DDI</PhoneType>
        </Phone>
        <Phone>
          <PhoneType>DEFAULT</PhoneType>
          <PhoneNumber>12344321</PhoneNumber>
          <PhoneAreaCode>03</PhoneAreaCode>
        </Phone>
        <Phone>
          <PhoneType>FAX</PhoneType>
        </Phone>
        <Phone>
          <PhoneType>MOBILE</PhoneType>
        </Phone>
      </Phones>
      <UpdatedDateUTC>2013-05-31T06:04:20.78</UpdatedDateUTC>
      <ContactGroups>
        <ContactGroup>
          <ContactGroupID>26fcca8d-a03b-4968-a80a-a463d5bf30ee</ContactGroupID>
          <Name>Support Clients (monthly)</Name>
          <Status>ACTIVE</Status>
        </ContactGroup>
      </ContactGroups>
      <IsSupplier>false</IsSupplier>
      <IsCustomer>true</IsCustomer>
    </Contact>
  </Contacts>
</Response>
"""
